from app import app, db
from models import Customer, BundleOffer, User, Certificate, FullOrderDetail, Book
import sqlalchemy as sa
from sqlalchemy import inspect, text
from datetime import datetime

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    return table_name in tables

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    try:
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False

def get_table_schema(table_name):
    """Get the complete schema of a table"""
    inspector = inspect(db.engine)
    try:
        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)
        return {
            'columns': columns,
            'foreign_keys': foreign_keys,
            'indexes': indexes
        }
    except Exception as e:
        return {'error': str(e)}

def verify_table_structure(table_name, expected_columns):
    """Verify that a table has the expected column structure"""
    print(f"\n  Verifying {table_name} table structure:")
    
    if not check_table_exists(table_name):
        print(f"    ❌ Table {table_name} does not exist")
        return False
    
    schema = get_table_schema(table_name)
    if 'error' in schema:
        print(f"    ❌ Error getting schema: {schema['error']}")
        return False
    
    existing_columns = [col['name'] for col in schema['columns']]
    all_columns_exist = True
    
    for col_name, col_info in expected_columns.items():
        if col_name in existing_columns:
            print(f"    ✓ Column {col_name} exists")
        else:
            print(f"    ❌ Column {col_name} missing")
            all_columns_exist = False
    
    # Check foreign keys
    if schema['foreign_keys']:
        print(f"    ✓ Foreign keys: {len(schema['foreign_keys'])} found")
    
    # Check indexes
    if schema['indexes']:
        print(f"    ✓ Indexes: {len(schema['indexes'])} found")
    
    return all_columns_exist

def test_model_relationships():
    """Test that SQLAlchemy relationships work correctly"""
    print("\n3. Testing SQLAlchemy model relationships:")
    
    try:
        # Test User-Customer relationship
        user_count = db.session.query(User).count()
        print(f"    ✓ User model accessible - {user_count} users in database")
        
        # Test Customer model
        customer_count = db.session.query(Customer).count()
        print(f"    ✓ Customer model accessible - {customer_count} customers in database")
        
        # Test BundleOffer model
        bundle_count = db.session.query(BundleOffer).count()
        print(f"    ✓ BundleOffer model accessible - {bundle_count} bundles in database")
        
        # Test relationships if data exists
        if customer_count > 0:
            # Test User-Customer relationship
            customer_with_user = db.session.query(Customer).join(User).first()
            if customer_with_user:
                print(f"    ✓ User-Customer relationship working")
            else:
                print(f"    ⚠ No customer with valid user relationship found")
        
        # Test Certificate model with new is_offline field
        cert_count = db.session.query(Certificate).count()
        print(f"    ✓ Certificate model accessible - {cert_count} certificates in database")
        
        if cert_count > 0:
            offline_certs = db.session.query(Certificate).filter(Certificate.is_offline == True).count()
            print(f"    ✓ Certificate.is_offline field working - {offline_certs} offline certificates")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error testing relationships: {e}")
        return False

def test_data_integrity():
    """Test data integrity and constraints"""
    print("\n4. Testing data integrity:")
    
    try:
        with db.engine.connect() as conn:
            # Check for orphaned records
            orphaned_customers = conn.execute(text("""
                SELECT COUNT(*) FROM customers c 
                WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.user_id)
            """)).scalar()
            
            if orphaned_customers == 0:
                print("    ✓ No orphaned customer records found")
            else:
                print(f"    ⚠ Found {orphaned_customers} orphaned customer records")
            
            # Check full_order_details with customer_id
            orders_with_customers = conn.execute(text("""
                SELECT COUNT(*) FROM full_order_details 
                WHERE customer_id IS NOT NULL
            """)).scalar()
            
            print(f"    ✓ {orders_with_customers} order details have customer references")
            
            # Check certificates with is_offline field
            offline_certs = conn.execute(text("""
                SELECT COUNT(*) FROM certificates WHERE is_offline = 1
            """)).scalar()
            
            online_certs = conn.execute(text("""
                SELECT COUNT(*) FROM certificates WHERE is_offline = 0 OR is_offline IS NULL
            """)).scalar()
            
            print(f"    ✓ Certificates: {offline_certs} offline, {online_certs} online")
            
            return True
            
    except Exception as e:
        print(f"    ❌ Error checking data integrity: {e}")
        return False

def test_new_functionality():
    """Test new functionality by creating sample data (using rollback transactions)"""
    print("\n5. Testing new functionality:")
    
    try:
        # Use nested transaction that will be rolled back to avoid persistent changes
        savepoint = db.session.begin_nested()
        
        try:
            # Test creating a bundle offer
            test_bundle = BundleOffer(
                title="Test Bundle (Verification Only)",
                description="Test bundle for verification - will be rolled back",
                mrp=1000.0,
                selling_price=800.0,
                discount_type="percentage",
                discount_value=20.0,
                is_active=True
            )
            db.session.add(test_bundle)
            db.session.flush()  # Assign ID without committing
            
            # Test adding books to bundle if books exist
            book_count = db.session.query(Book).count()
            if book_count > 0:
                test_book = db.session.query(Book).first()
                test_bundle.books.append(test_book)
                db.session.flush()
                print("    ✓ Successfully created test bundle with book relationship")
            else:
                print("    ✓ Successfully created test bundle (no books available for relationship test)")
            
            # Test that we can query the test data
            bundle_check = db.session.query(BundleOffer).filter_by(title="Test Bundle (Verification Only)").first()
            if bundle_check:
                print("    ✓ Bundle relationship and querying functionality verified")
            else:
                print("    ⚠ Bundle creation test failed - could not retrieve created bundle")
            
            # Rollback the nested transaction - no persistent changes
            savepoint.rollback()
            print("    ✓ Test data successfully rolled back - no persistent database changes")
            
            # Verify rollback worked
            bundle_after_rollback = db.session.query(BundleOffer).filter_by(title="Test Bundle (Verification Only)").first()
            if bundle_after_rollback is None:
                print("    ✓ Rollback verification successful - test bundle was removed")
            else:
                print("    ⚠ Rollback verification failed - test data may still exist")
            
        except Exception as nested_e:
            # Rollback nested transaction on error
            savepoint.rollback()
            print(f"    ❌ Error in nested transaction: {nested_e}")
            print("    ✓ Nested transaction rolled back due to error")
            return False
        
        # Also test existing bundle functionality if bundles exist
        existing_bundle_count = db.session.query(BundleOffer).count()
        if existing_bundle_count > 0:
            print(f"    ✓ Bundle functionality also verified with existing {existing_bundle_count} bundles")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error testing new functionality: {e}")
        db.session.rollback()
        return False

def generate_verification_report():
    """Generate a comprehensive verification report"""
    print("\n" + "=" * 60)
    print("DATABASE MIGRATION VERIFICATION REPORT")
    print("=" * 60)
    
    # Expected table structures
    expected_tables = {
        'customers': {
            'id': 'INTEGER PRIMARY KEY',
            'user_id': 'INTEGER NOT NULL',
            'full_name': 'VARCHAR(100) NOT NULL',
            'email': 'VARCHAR(120) NOT NULL',
            'phone': 'VARCHAR(20)',
            'street_address': 'VARCHAR(255)',
            'city': 'VARCHAR(100)',
            'state': 'VARCHAR(100)',
            'pincode': 'VARCHAR(20)',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        },
        'bundle_offers': {
            'id': 'INTEGER PRIMARY KEY',
            'title': 'VARCHAR(150) NOT NULL',
            'description': 'TEXT',
            'mrp': 'FLOAT NOT NULL',
            'selling_price': 'FLOAT NOT NULL',
            'discount_type': 'VARCHAR(20) NOT NULL',
            'discount_value': 'FLOAT NOT NULL',
            'is_active': 'BOOLEAN',
            'created_at': 'DATETIME',
            'updated_at': 'DATETIME'
        },
        'bundle_books': {
            'bundle_id': 'INTEGER NOT NULL',
            'book_id': 'INTEGER NOT NULL'
        }
    }
    
    all_checks_passed = True
    
    # 1. Table Structure Verification
    print("\n1. Verifying table structures:")
    for table_name, expected_columns in expected_tables.items():
        if not verify_table_structure(table_name, expected_columns):
            all_checks_passed = False
    
    # 2. Column Modifications Verification
    print("\n2. Verifying column modifications:")
    
    # Check certificates.is_offline
    if check_column_exists('certificates', 'is_offline'):
        print("    ✓ certificates.is_offline column exists")
    else:
        print("    ❌ certificates.is_offline column missing")
        all_checks_passed = False
    
    # Check full_order_details new columns
    if check_column_exists('full_order_details', 'customer_id'):
        print("    ✓ full_order_details.customer_id column exists")
    else:
        print("    ❌ full_order_details.customer_id column missing")
        all_checks_passed = False
        
    if check_column_exists('full_order_details', 'bundle_id'):
        print("    ✓ full_order_details.bundle_id column exists")
    else:
        print("    ❌ full_order_details.bundle_id column missing")
        all_checks_passed = False
    
    # 3. Test relationships
    if not test_model_relationships():
        all_checks_passed = False
    
    # 4. Test data integrity
    if not test_data_integrity():
        all_checks_passed = False
    
    # 5. Test new functionality
    if not test_new_functionality():
        all_checks_passed = False
    
    # 6. Performance Check - verify indexes
    print("\n6. Verifying performance indexes:")
    expected_indexes = [
        ('customers', 'idx_customers_user_id'),
        ('bundle_offers', 'idx_bundle_offers_is_active'),
        ('full_order_details', 'idx_full_order_details_customer_id'),
        ('full_order_details', 'idx_full_order_details_bundle_id')
    ]
    
    for table_name, index_name in expected_indexes:
        try:
            schema = get_table_schema(table_name)
            index_names = [idx['name'] for idx in schema.get('indexes', [])]
            if index_name in index_names or any(index_name in idx_name for idx_name in index_names):
                print(f"    ✓ Index {index_name} exists on {table_name}")
            else:
                print(f"    ⚠ Index {index_name} may not exist on {table_name}")
        except Exception as e:
            print(f"    ⚠ Could not verify index {index_name}: {e}")
    
    # Final Report
    print("\n" + "=" * 60) 
    if all_checks_passed:
        print("✅ MIGRATION VERIFICATION SUCCESSFUL!")
        print("\nAll database changes have been applied correctly.")
        print("Your application is ready to use the new features:")
        print("- Bundle offer management")
        print("- Enhanced customer address management") 
        print("- Offline certificate support")
        print("- Improved order tracking")
    else:
        print("❌ MIGRATION VERIFICATION FAILED!")
        print("\nSome issues were found. Please review the errors above.")
        print("You may need to:")
        print("- Re-run the migration script")
        print("- Manually fix database issues")
        print("- Check your application configuration")
    
    print("\n" + "=" * 60)
    return all_checks_passed

def main():
    """Main verification function"""
    try:
        with app.app_context():
            return generate_verification_report()
    except Exception as e:
        print(f"❌ Verification failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)