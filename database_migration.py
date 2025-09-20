from app import app, db
from models import Customer, BundleOffer, User, Certificate, FullOrderDetail
import sqlalchemy as sa
from sqlalchemy import inspect, text
from datetime import datetime, timezone

def add_column_if_not_exists(table_name, column_name, column_type):
    """Add a column to a table if it doesn't already exist"""
    inspector = inspect(db.engine)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    
    if column_name not in columns:
        with db.engine.connect() as conn:
            conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}'))
            conn.commit()
        print(f"✓ Added column {column_name} to {table_name}")
        return True
    else:
        print(f"- Column {column_name} already exists in {table_name}")
        return False

def create_table_if_not_exists(table_name, create_sql):
    """Create a table if it doesn't already exist"""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if table_name not in tables:
        with db.engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()
        print(f"✓ Created table {table_name}")
        return True
    else:
        print(f"- Table {table_name} already exists")
        return False

def create_index_if_not_exists(index_name, table_name, column_name):
    """Create an index if it doesn't already exist"""
    try:
        with db.engine.connect() as conn:
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})'))
            conn.commit()
        print(f"✓ Created index {index_name} on {table_name}.{column_name}")
    except Exception as e:
        print(f"- Index {index_name} may already exist: {e}")

def migrate_address_data():
    """Migrate existing address data from full_order_details to customers table"""
    try:
        with db.engine.connect() as conn:
            # Get distinct user addresses from full_order_details
            result = conn.execute(text("""
                SELECT DISTINCT 
                    o.user_id,
                    fod.full_name,
                    fod.email,
                    fod.phone,
                    fod.address
                FROM full_order_details fod
                JOIN orders o ON fod.order_id = o.id
                WHERE fod.full_name IS NOT NULL 
                AND fod.email IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM customers c WHERE c.user_id = o.user_id
                )
            """))
            
            customers_created = 0
            for row in result:
                # Parse address into components (basic parsing)
                address_parts = row.address.split(',') if row.address else ['', '', '', '']
                street = address_parts[0].strip() if len(address_parts) > 0 else ''
                city = address_parts[1].strip() if len(address_parts) > 1 else ''
                state = address_parts[2].strip() if len(address_parts) > 2 else ''
                pincode = address_parts[3].strip() if len(address_parts) > 3 else ''
                
                # Insert customer record
                conn.execute(text("""
                    INSERT INTO customers (user_id, full_name, email, phone, street_address, city, state, pincode, created_at, updated_at)
                    VALUES (:user_id, :full_name, :email, :phone, :street_address, :city, :state, :pincode, :created_at, :updated_at)
                """), {
                    'user_id': row.user_id,
                    'full_name': row.full_name,
                    'email': row.email,
                    'phone': row.phone,
                    'street_address': street,
                    'city': city,
                    'state': state,
                    'pincode': pincode,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc)
                })
                customers_created += 1
            
            conn.commit()
            print(f"✓ Migrated {customers_created} customer records from existing order data")
            
    except Exception as e:
        print(f"⚠ Error migrating address data: {e}")

def update_full_order_details_with_customer_ids():
    """Update full_order_details with customer_id references"""
    try:
        with db.engine.connect() as conn:
            # Update full_order_details to reference customer records
            result = conn.execute(text("""
                UPDATE full_order_details 
                SET customer_id = (
                    SELECT c.id 
                    FROM customers c 
                    JOIN orders o ON c.user_id = o.user_id 
                    WHERE o.id = full_order_details.order_id
                    LIMIT 1
                )
                WHERE customer_id IS NULL
                AND EXISTS (
                    SELECT 1 
                    FROM customers c 
                    JOIN orders o ON c.user_id = o.user_id 
                    WHERE o.id = full_order_details.order_id
                )
            """))
            conn.commit()
            print(f"✓ Updated {result.rowcount} full_order_details records with customer_id references")
            
    except Exception as e:
        print(f"⚠ Error updating full_order_details with customer_ids: {e}")

def rebuild_certificates_table_for_nullable_course_id():
    """Rebuild certificates table to make course_id nullable (SQLite approach)"""
    try:
        # Check if course_id is already nullable
        inspector = inspect(db.engine)
        cert_columns = {col['name']: col for col in inspector.get_columns('certificates')}
        
        if 'course_id' not in cert_columns:
            print("- certificates table doesn't have course_id column")
            return
            
        if cert_columns['course_id']['nullable']:
            print("- certificates.course_id is already nullable")
            return
            
        print("    Rebuilding certificates table to make course_id nullable...")
        
        with db.engine.connect() as conn:
            # Create temporary table with desired schema
            conn.execute(text("""
                CREATE TABLE certificates_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER,
                    is_offline BOOLEAN DEFAULT 0,
                    filename VARCHAR(255) NOT NULL,
                    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (course_id) REFERENCES courses (id)
                )
            """))
            
            # Copy data from original table
            conn.execute(text("""
                INSERT INTO certificates_temp (id, user_id, course_id, is_offline, filename, upload_date)
                SELECT id, user_id, course_id, 
                       COALESCE(is_offline, 0) as is_offline,
                       filename, upload_date
                FROM certificates
            """))
            
            # Drop original table
            conn.execute(text("DROP TABLE certificates"))
            
            # Rename temp table to original name
            conn.execute(text("ALTER TABLE certificates_temp RENAME TO certificates"))
            
            conn.commit()
            
        print("    ✓ Successfully rebuilt certificates table with nullable course_id")
        
    except Exception as e:
        print(f"    ⚠ Error rebuilding certificates table: {e}")

def validate_and_cleanup_order_details_data():
    """Validate and optionally cleanup inconsistent order details data before constraint application"""
    try:
        with db.engine.connect() as conn:
            # Check for bundle orders where item_id != bundle_id
            result = conn.execute(text("""
                SELECT COUNT(*) FROM full_order_details 
                WHERE item_type = 'bundle' 
                AND bundle_id IS NOT NULL 
                AND item_id != bundle_id
            """))
            
            inconsistent_bundles = result.scalar() or 0
            
            if inconsistent_bundles > 0:
                print(f"    ⚠ Found {inconsistent_bundles} bundle orders with item_id != bundle_id")
                
                # Show sample of inconsistent data
                sample_result = conn.execute(text("""
                    SELECT id, item_id, bundle_id, item_title 
                    FROM full_order_details 
                    WHERE item_type = 'bundle' 
                    AND bundle_id IS NOT NULL 
                    AND item_id != bundle_id 
                    LIMIT 5
                """))
                
                print("    Sample inconsistent records:")
                for row in sample_result:
                    print(f"      ID: {row.id}, item_id: {row.item_id}, bundle_id: {row.bundle_id}, title: {row.item_title}")
                
                # Offer to fix the data automatically
                response = input("    Fix inconsistent data by setting item_id = bundle_id? (y/N): ")
                if response.lower() == 'y':
                    # Update inconsistent records
                    update_result = conn.execute(text("""
                        UPDATE full_order_details 
                        SET item_id = bundle_id 
                        WHERE item_type = 'bundle' 
                        AND bundle_id IS NOT NULL 
                        AND item_id != bundle_id
                    """))
                    conn.commit()
                    print(f"    ✓ Fixed {update_result.rowcount} inconsistent bundle records")
                else:
                    print("    ❌ Cannot proceed with constraint creation - data inconsistency exists")
                    print("    Please fix the data manually or choose to auto-fix when prompted")
                    return False
            
            # Check for non-bundle orders with bundle_id set
            result = conn.execute(text("""
                SELECT COUNT(*) FROM full_order_details 
                WHERE item_type != 'bundle' 
                AND bundle_id IS NOT NULL
            """))
            
            inconsistent_non_bundles = result.scalar() or 0
            
            if inconsistent_non_bundles > 0:
                print(f"    ⚠ Found {inconsistent_non_bundles} non-bundle orders with bundle_id set")
                
                # Offer to fix the data automatically
                response = input("    Fix by setting bundle_id = NULL for non-bundle orders? (y/N): ")
                if response.lower() == 'y':
                    update_result = conn.execute(text("""
                        UPDATE full_order_details 
                        SET bundle_id = NULL 
                        WHERE item_type != 'bundle' 
                        AND bundle_id IS NOT NULL
                    """))
                    conn.commit()
                    print(f"    ✓ Fixed {update_result.rowcount} inconsistent non-bundle records")
                else:
                    print("    ❌ Cannot proceed with constraint creation - data inconsistency exists")
                    return False
            
            if inconsistent_bundles == 0 and inconsistent_non_bundles == 0:
                print("    ✓ No data inconsistencies found - safe to proceed with constraints")
            
            return True
            
    except Exception as e:
        print(f"    ⚠ Error validating order details data: {e}")
        return False

def rebuild_full_order_details_with_foreign_keys():
    """Rebuild full_order_details table with proper foreign key constraints"""
    try:
        # Check if foreign keys already exist
        inspector = inspect(db.engine)
        fks = inspector.get_foreign_keys('full_order_details')
        
        existing_fk_columns = set()
        for fk in fks:
            existing_fk_columns.update(fk['constrained_columns'])
        
        needs_customer_fk = 'customer_id' not in existing_fk_columns
        needs_bundle_fk = 'bundle_id' not in existing_fk_columns
        
        if not needs_customer_fk and not needs_bundle_fk:
            print("    - full_order_details already has required foreign keys")
            return
        
        # Validate and cleanup data before applying constraints
        if not validate_and_cleanup_order_details_data():
            print("    ❌ Skipping table rebuild due to data validation failures")
            return
            
        print("    Rebuilding full_order_details table with foreign key constraints...")
        
        with db.engine.connect() as conn:
            # Create temporary table with proper foreign keys
            conn.execute(text("""
                CREATE TABLE full_order_details_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    transaction_id INTEGER,
                    customer_id INTEGER,
                    bundle_id INTEGER,
                    custom_order_id VARCHAR(30),
                    item_id INTEGER NOT NULL,
                    item_type VARCHAR(20) NOT NULL,
                    item_title VARCHAR(150) NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    price FLOAT NOT NULL,
                    full_name VARCHAR(100),
                    email VARCHAR(100),
                    phone VARCHAR(20),
                    address VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (id),
                    FOREIGN KEY (transaction_id) REFERENCES transactions (id),
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (bundle_id) REFERENCES bundle_offers (id),
                    CHECK (
                        (item_type = 'bundle' AND bundle_id IS NOT NULL AND item_id = bundle_id) OR
                        (item_type != 'bundle' AND bundle_id IS NULL)
                    )
                )
            """))
            
            # Copy data from original table
            columns_to_copy = [
                'id', 'order_id', 'transaction_id', 'custom_order_id', 
                'item_id', 'item_type', 'item_title', 'quantity', 'price',
                'full_name', 'email', 'phone', 'address', 'created_at'
            ]
            
            # Check if new columns exist in original table
            original_columns = inspector.get_columns('full_order_details')
            original_column_names = [col['name'] for col in original_columns]
            
            if 'customer_id' in original_column_names:
                columns_to_copy.append('customer_id')
            if 'bundle_id' in original_column_names:
                columns_to_copy.append('bundle_id')
                
            columns_sql = ', '.join(columns_to_copy)
            
            conn.execute(text(f"""
                INSERT INTO full_order_details_temp ({columns_sql})
                SELECT {columns_sql}
                FROM full_order_details
            """))
            
            # Drop original table
            conn.execute(text("DROP TABLE full_order_details"))
            
            # Rename temp table to original name
            conn.execute(text("ALTER TABLE full_order_details_temp RENAME TO full_order_details"))
            
            conn.commit()
            
        print("    ✓ Successfully rebuilt full_order_details table with foreign key constraints")
        
    except Exception as e:
        print(f"    ⚠ Error rebuilding full_order_details table: {e}")

def check_for_schema_drift():
    """Check for schema drift if db.create_all() was run before migration"""
    print("0. Checking for potential schema drift:")
    
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        issues_found = False
        
        # Check if customers table exists with unexpected schema
        if 'customers' in tables:
            columns = inspector.get_columns('customers')
            column_names = [col['name'] for col in columns]
            expected_columns = ['id', 'user_id', 'full_name', 'email', 'phone', 
                              'street_address', 'city', 'state', 'pincode', 
                              'created_at', 'updated_at']
            
            missing_columns = set(expected_columns) - set(column_names)
            extra_columns = set(column_names) - set(expected_columns)
            
            if missing_columns or extra_columns:
                print(f"    ⚠ customers table schema mismatch detected!")
                if missing_columns:
                    print(f"      Missing columns: {missing_columns}")
                if extra_columns:
                    print(f"      Extra columns: {extra_columns}")
                issues_found = True
        
        # Check if bundle_offers table exists with unexpected schema
        if 'bundle_offers' in tables:
            columns = inspector.get_columns('bundle_offers')
            column_names = [col['name'] for col in columns]
            expected_columns = ['id', 'title', 'description', 'mrp', 'selling_price',
                              'discount_type', 'discount_value', 'is_active',
                              'created_at', 'updated_at']
            
            missing_columns = set(expected_columns) - set(column_names)
            extra_columns = set(column_names) - set(expected_columns)
            
            if missing_columns or extra_columns:
                print(f"    ⚠ bundle_offers table schema mismatch detected!")
                if missing_columns:
                    print(f"      Missing columns: {missing_columns}")
                if extra_columns:
                    print(f"      Extra columns: {extra_columns}")
                issues_found = True
        
        if issues_found:
            print(f"    ⚠ Schema drift detected! This may happen if db.create_all() was run before migration.")
            print(f"    ⚠ The migration will attempt to reconcile differences, but backup your database first!")
            print(f"    ⚠ Consider dropping the affected tables and re-running migration for clean schema.")
            response = input("    Continue with migration? (y/N): ")
            if response.lower() != 'y':
                print("    Migration aborted by user.")
                return False
        else:
            print("    ✓ No schema drift detected")
            
        return True
        
    except Exception as e:
        print(f"    ⚠ Error checking for schema drift: {e}")
        return True  # Continue migration despite check failure

def run_migration():
    """Main migration function"""
    print("Starting database migration...")
    print("=" * 50)
    
    # Pre-migration schema drift check
    if not check_for_schema_drift():
        return False
    
    try:
        # Step 1: Create new tables
        print("\n1. Creating new tables:")
        
        # Create customers table
        customers_sql = """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(120) NOT NULL,
            phone VARCHAR(20),
            street_address VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            pincode VARCHAR(20),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
        create_table_if_not_exists('customers', customers_sql)
        
        # Create bundle_offers table
        bundle_offers_sql = """
        CREATE TABLE IF NOT EXISTS bundle_offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(150) NOT NULL,
            description TEXT,
            mrp FLOAT NOT NULL,
            selling_price FLOAT NOT NULL,
            discount_type VARCHAR(20) NOT NULL DEFAULT 'percentage',
            discount_value FLOAT NOT NULL DEFAULT 0.0,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        create_table_if_not_exists('bundle_offers', bundle_offers_sql)
        
        # Create bundle_books association table
        bundle_books_sql = """
        CREATE TABLE IF NOT EXISTS bundle_books (
            bundle_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            PRIMARY KEY (bundle_id, book_id),
            FOREIGN KEY (bundle_id) REFERENCES bundle_offers (id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
        )
        """
        create_table_if_not_exists('bundle_books', bundle_books_sql)
        
        # Step 2: Add new columns to existing tables
        print("\n2. Adding new columns to existing tables:")
        
        # Add is_offline column to certificates table
        add_column_if_not_exists('certificates', 'is_offline', 'BOOLEAN DEFAULT 0')
        
        # Add bundle_id and customer_id columns to full_order_details table
        add_column_if_not_exists('full_order_details', 'bundle_id', 'INTEGER')
        add_column_if_not_exists('full_order_details', 'customer_id', 'INTEGER') 
        
        # Step 3: Modify existing columns (make course_id nullable in certificates)
        print("\n3. Modifying existing columns:")
        rebuild_certificates_table_for_nullable_course_id()
        
        # Step 3.5: Add foreign key constraints to full_order_details
        print("\n3.5. Adding foreign key constraints:")
        rebuild_full_order_details_with_foreign_keys()
        
        # Step 4: Create indexes for performance
        print("\n4. Creating indexes:")
        create_index_if_not_exists('idx_customers_user_id', 'customers', 'user_id')
        # Create unique index for one-to-one User-Customer relationship
        try:
            with db.engine.connect() as conn:
                conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_user_id ON customers (user_id)'))
                conn.commit()
            print("✓ Created unique index uq_customers_user_id on customers.user_id")
        except Exception as e:
            print(f"- Unique index uq_customers_user_id may already exist: {e}")
        create_index_if_not_exists('idx_bundle_offers_is_active', 'bundle_offers', 'is_active')
        create_index_if_not_exists('idx_full_order_details_customer_id', 'full_order_details', 'customer_id')
        create_index_if_not_exists('idx_full_order_details_bundle_id', 'full_order_details', 'bundle_id')
        
        # Step 5: Migrate existing data
        print("\n5. Migrating existing data:")
        migrate_address_data()
        update_full_order_details_with_customer_ids()
        
        # Step 6: Update default values for existing records
        print("\n6. Setting default values for existing records:")
        try:
            with db.engine.connect() as conn:
                # Set is_offline = False for existing certificates
                result = conn.execute(text("UPDATE certificates SET is_offline = 0 WHERE is_offline IS NULL"))
                conn.commit()
                print(f"✓ Updated {result.rowcount} certificates with is_offline = False")
        except Exception as e:
            print(f"⚠ Error setting default values: {e}")
        
        print("\n" + "=" * 50)
        print("✓ Database migration completed successfully!")
        print("\nNext steps:")
        print("1. Run 'python verify_migration.py' to verify the migration")
        print("2. Test your application with the new schema")
        print("3. Update your application code to use the new models")
        
    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        print("Please check the error and try again.")
        return False
    
    return True

if __name__ == "__main__":
    with app.app_context():
        run_migration()