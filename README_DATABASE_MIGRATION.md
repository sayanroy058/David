# Database Migration Guide

## Overview

This document describes the comprehensive database schema updates implemented to enhance the application with new features including bundle offers, detailed customer management, and offline certificate support.

### Migration Summary

The migration adds new tables and modifies existing ones to support:
- **Bundle Offer Management**: Create and manage bundle deals with books
- **Enhanced Customer Management**: Detailed address components and user relationships  
- **Offline Certificate Support**: Standalone certificates not tied to courses
- **Improved Order Tracking**: Better customer and bundle support in order details

## New Database Schema

### New Tables

#### 1. `customers` Table
Stores detailed customer information with enhanced address components.

```sql
CREATE TABLE customers (
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
);
```

**Purpose**: Replaces the simple address field in `full_order_details` with structured address components.

**Relationships**:
- One-to-One with `users` table
- One-to-Many with `full_order_details` table

#### 2. `bundle_offers` Table  
Manages bundle deals with multiple books at discounted prices.

```sql
CREATE TABLE bundle_offers (
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
);
```

**Purpose**: Creates bundle offers containing multiple books with pricing and discount management.

**Fields**:
- `discount_type`: Either 'percentage' or 'fixed'
- `discount_value`: Discount amount (percentage or fixed value)
- `is_active`: Enable/disable bundle offers

#### 3. `bundle_books` Association Table
Many-to-many relationship between bundles and books.

```sql
CREATE TABLE bundle_books (
    bundle_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    PRIMARY KEY (bundle_id, book_id),
    FOREIGN KEY (bundle_id) REFERENCES bundle_offers (id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
);
```

**Purpose**: Links books to bundle offers allowing flexible bundle composition.

### Modified Tables

#### 1. `certificates` Table Modifications
- **Added**: `is_offline BOOLEAN DEFAULT 0` - Support for standalone certificates
- **Modified**: `course_id` is now nullable - Allows certificates not tied to courses

#### 2. `full_order_details` Table Modifications  
- **Added**: `customer_id INTEGER` - Foreign key to customers table
- **Added**: `bundle_id INTEGER` - Foreign key to bundle_offers table
- **Enhanced**: `item_type` field now supports 'bundle' in addition to existing types

#### 3. `users` Table Modifications
- **Added**: One-to-One relationship with Customer model

## Migration Instructions

### Prerequisites

1. **Backup your database** before running the migration:
   ```bash
   cp instance/site.db instance/site.db.backup
   ```

2. **Ensure your virtual environment is activated**:
   ```bash
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\\Scripts\\activate   # On Windows
   ```

3. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **⚠️ IMPORTANT: Migration Order**:
   **Run this migration BEFORE any `db.create_all()` calls in your application code.**
   
   If `db.create_all()` has already been run, the migration includes schema drift detection that will:
   - Compare existing table schemas against expected migration schemas
   - Warn about potential conflicts and offer to continue or abort
   - Attempt to reconcile differences automatically
   
   For the cleanest migration, ensure this runs on a database that hasn't had `db.create_all()` executed with the new models.

### Running the Migration

1. **Execute the migration script**:
   ```bash
   python database_migration.py
   ```

   Expected output:
   ```
   Starting database migration...
   ==================================================
   
   0. Checking for potential schema drift:
   ✓ No schema drift detected
   
   1. Creating new tables:
   ✓ Created table customers
   ✓ Created table bundle_offers
   ✓ Created table bundle_books
   
   2. Adding new columns to existing tables:
   ✓ Added column is_offline to certificates
   ✓ Added column bundle_id to full_order_details
   ✓ Added column customer_id to full_order_details
   
   3. Modifying existing columns:
       ✓ Successfully rebuilt certificates table with nullable course_id
   
   3.5. Adding foreign key constraints:
   ✓ No data inconsistencies found - safe to proceed with constraints
   ✓ Successfully rebuilt full_order_details table with foreign key constraints
   
   4. Creating indexes:
   ✓ Created index idx_customers_user_id on customers.user_id
   ✓ Created index idx_bundle_offers_is_active on bundle_offers.is_active
   ✓ Created index idx_full_order_details_customer_id on full_order_details.customer_id
   ✓ Created index idx_full_order_details_bundle_id on full_order_details.bundle_id
   
   5. Migrating existing data:
   ✓ Migrated 15 customer records from existing order data
   ✓ Updated 25 full_order_details records with customer_id references
   
   6. Setting default values for existing records:
   ✓ Updated 8 certificates with is_offline = False
   
   ==================================================
   ✓ Database migration completed successfully!
   ```

2. **Verify the migration**:
   ```bash
   python verify_migration.py
   ```

   This will run comprehensive checks and generate a detailed verification report.

### Verification

The verification script checks:
- ✅ New table creation and structure
- ✅ Column additions and modifications  
- ✅ SQLAlchemy model relationships
- ✅ Data integrity and constraints
- ✅ Index creation for performance
- ✅ Sample functionality testing

## Breaking Changes

### 1. Certificate Model Changes

**Before**:
```python
# course_id was required
certificate = Certificate(user_id=1, course_id=5, filename="cert.pdf")
```

**After**:  
```python
# course_id is now optional for offline certificates
certificate = Certificate(user_id=1, filename="cert.pdf", is_offline=True)
# or for course certificates
certificate = Certificate(user_id=1, course_id=5, filename="cert.pdf", is_offline=False)
```

### 2. Customer Information Handling

**Before**:
```python
# Address stored as single string in full_order_details
order_detail.address = "123 Main St, City, State, 12345"
```

**After**:
```python
# Customer information stored in separate customer table
customer = Customer(
    user_id=1,
    full_name="John Doe", 
    email="john@example.com",
    street_address="123 Main St",
    city="City",
    state="State", 
    pincode="12345"
)
order_detail.customer_id = customer.id
```

### 3. Bundle Support in Orders

**New functionality** - item_type can now be 'bundle':
```python
order_detail = FullOrderDetail(
    item_type='bundle',
    item_id=bundle.id,
    bundle_id=bundle.id,
    item_title=bundle.title,
    price=bundle.selling_price
)
```

## New Features Enabled

### 1. Bundle Offer Management

```python
# Create a bundle offer
bundle = BundleOffer(
    title="Python Programming Bundle",
    description="Complete Python learning bundle",
    mrp=1500.0,
    selling_price=1200.0,
    discount_type="percentage",
    discount_value=20.0,
    is_active=True
)

# Add books to bundle
bundle.books.append(book1)
bundle.books.append(book2)
db.session.add(bundle)
db.session.commit()
```

### 2. Enhanced Customer Management

```python
# Create detailed customer profile
customer = Customer(
    user_id=user.id,
    full_name="Jane Smith",
    email="jane@example.com", 
    phone="+1234567890",
    street_address="456 Oak Avenue",
    city="Springfield",
    state="Illinois",
    pincode="62701"
)
db.session.add(customer)
db.session.commit()
```

### 3. Offline Certificate Support

```python  
# Create standalone certificate
offline_cert = Certificate(
    user_id=user.id,
    filename="completion_certificate.pdf",
    is_offline=True  # Not tied to any course
)
db.session.add(offline_cert)
db.session.commit()
```

### 4. Improved Order Tracking

```python
# Orders now reference customer details
order_detail = FullOrderDetail(
    order_id=order.id,
    customer_id=customer.id,  # Reference to customer table
    item_type='book',
    item_id=book.id,
    item_title=book.title,
    quantity=1,
    price=book.price
)
```

### 5. FullOrderDetail Data Consistency Rules

**⚠️ IMPORTANT: Bundle Reference Synchronization**

The `FullOrderDetail` model now has both `item_id` and `bundle_id` fields. To maintain data consistency:

**For Bundle Orders**:
```python
# When item_type='bundle', bundle_id MUST be set and synchronized with item_id
order_detail = FullOrderDetail(
    item_type='bundle',
    item_id=bundle.id,      # Must match bundle_id
    bundle_id=bundle.id,    # Must match item_id  
    item_title=bundle.title,
    price=bundle.selling_price
)
```

**For Non-Bundle Orders**:
```python
# When item_type != 'bundle', bundle_id MUST be NULL
order_detail = FullOrderDetail(
    item_type='book',       # or 'course'
    item_id=book.id,        # References the actual item
    bundle_id=None,         # Must be NULL for non-bundles
    item_title=book.title,
    price=book.price
)
```

**Database-Level Constraints**:
The migration adds a CHECK constraint to enforce strict synchronization:
```sql
CHECK (
    (item_type = 'bundle' AND bundle_id IS NOT NULL AND item_id = bundle_id) OR
    (item_type != 'bundle' AND bundle_id IS NULL)
)
```

This constraint ensures:
- For bundle orders: `bundle_id` must be set AND must equal `item_id`
- For non-bundle orders: `bundle_id` must be NULL
- No drift between `item_id` and `bundle_id` is possible at the database level

**Application-Level Validation** (Recommended):
```python
def validate_order_detail(order_detail):
    """Validate FullOrderDetail consistency"""
    if order_detail.item_type == 'bundle':
        if order_detail.bundle_id is None:
            raise ValueError("bundle_id must be set when item_type='bundle'")
        if order_detail.item_id != order_detail.bundle_id:
            raise ValueError("item_id must equal bundle_id when item_type='bundle'")
    else:
        if order_detail.bundle_id is not None:
            raise ValueError("bundle_id must be NULL when item_type != 'bundle'")
```

## Rollback Instructions

### Automated Rollback (Recommended)

If you need to rollback the migration:

1. **Restore from backup**:
   ```bash
   cp instance/site.db.backup instance/site.db
   ```

2. **Revert code changes**:
   ```bash
   git checkout HEAD~1 models.py  # If using git
   ```

### Manual Rollback

If backup restoration isn't possible:

1. **Drop new tables**:
   ```sql
   DROP TABLE IF EXISTS bundle_books;
   DROP TABLE IF EXISTS bundle_offers;  
   DROP TABLE IF EXISTS customers;
   ```

2. **Remove new columns**:
   ```sql
   -- SQLite doesn't support DROP COLUMN, so you'd need to recreate tables
   -- This is complex and backup restoration is recommended instead
   ```

### Code Rollback

Remove the following from `models.py`:
- `Customer` class
- `BundleOffer` class  
- `bundle_books` association table
- `is_offline` field from `Certificate`
- `customer_id` and `bundle_id` fields from `FullOrderDetail`
- Customer relationship from `User`

## Testing

### Manual Testing

1. **Test bundle creation**:
   ```python
   from models import BundleOffer, Book
   
   # Create test bundle
   bundle = BundleOffer(title="Test Bundle", mrp=100, selling_price=80)
   bundle.books.append(Book.query.first())
   db.session.add(bundle)
   db.session.commit()
   ```

2. **Test customer creation**:
   ```python
   from models import Customer, User
   
   # Create test customer
   user = User.query.first()
   customer = Customer(
       user_id=user.id,
       full_name="Test User",
       email="test@example.com"
   )
   db.session.add(customer)
   db.session.commit()
   ```

3. **Test offline certificates**:
   ```python
   from models import Certificate, User
   
   # Create offline certificate
   user = User.query.first()
   cert = Certificate(
       user_id=user.id,
       filename="test_cert.pdf",
       is_offline=True
   )
   db.session.add(cert)
   db.session.commit()
   ```

### Integration Testing

Run the application and test:
- Bundle offer creation in admin panel
- Customer profile management
- Order placement with bundle items
- Certificate upload for offline certificates

## Troubleshooting

### Common Issues

1. **"Table already exists" errors**:
   - This is normal for idempotent migration - tables won't be recreated
   - Check verification script output for confirmation

2. **Foreign key constraint errors**:
   - Ensure all referenced tables exist
   - Check that user_id values in customers table are valid

3. **SQLAlchemy relationship errors**:
   - Restart your application after migration
   - Clear any cached model definitions

4. **Migration script failures**:
   - Check database permissions
   - Ensure no other processes are using the database
   - Review error messages for specific issues

5. **Data validation errors during constraint creation**:
   - Migration detects inconsistent bundle order data (item_id != bundle_id)
   - Migration offers to auto-fix by setting item_id = bundle_id
   - Choose 'y' to auto-fix or manually correct data before re-running migration
   - For non-bundle orders with bundle_id set, migration offers to set bundle_id = NULL

### Getting Help

If you encounter issues:

1. **Check the verification report**: `python verify_migration.py`
2. **Review migration logs** for specific error messages
3. **Restore from backup** if needed: `cp instance/site.db.backup instance/site.db`
4. **Check database file permissions** and SQLite version compatibility

## Performance Considerations

### Indexes Created

The migration creates the following indexes for optimal performance:

- `idx_customers_user_id`: Fast user-customer lookups
- `idx_bundle_offers_is_active`: Filter active bundles efficiently  
- `idx_full_order_details_customer_id`: Fast customer order history
- `idx_full_order_details_bundle_id`: Bundle order tracking

### Query Optimization

With the new schema:
- Customer lookups are faster with dedicated customer table
- Bundle queries benefit from proper indexing
- Order history queries can leverage customer relationships

## Conclusion

This migration significantly enhances the application's capabilities while maintaining backward compatibility. The new features enable:

- **Advanced e-commerce functionality** with bundle offers
- **Better customer experience** with detailed address management  
- **Flexible certification system** supporting both course and standalone certificates
- **Improved data organization** with proper relationships and constraints

After running the migration and verification successfully, your application will be ready to leverage these enhanced features.

---

**Migration Version**: 1.0  
**Created**: September 2025  
**Author**: Database Migration Script  
**Compatibility**: SQLite 3.x, Flask-SQLAlchemy 2.x+