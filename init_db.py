from app import app
from models import db, Book, Category, SubCategory

with app.app_context():
    # Create new tables if not exist
    db.create_all()

    # Migrate old data if old columns still exist
    # (only works if you haven't removed category/subject columns yet)
    try:
        books = Book.query.all()
        for b in books:
            if hasattr(b, "category") and b.category:
                cat = Category.query.filter_by(name=b.category).first()
                if not cat:
                    cat = Category(name=b.category)
                    db.session.add(cat)
                if cat not in b.categories:
                    b.categories.append(cat)

            if hasattr(b, "subject") and b.subject:
                sub = SubCategory.query.filter_by(name=b.subject).first()
                if not sub:
                    # Attach subcategory to first category if possible
                    sub = SubCategory(name=b.subject, category=cat if b.category else None)
                    db.session.add(sub)
                if sub not in b.subcategories:
                    b.subcategories.append(sub)

        db.session.commit()
        print("✅ Old category/subject values migrated to new tables.")
    except Exception as e:
        print("⚠️ Migration skipped (maybe old columns already dropped):", e)
