# Banner Responsive Update - Mobile & PC Support

## Overview
This update adds support for separate banner images for mobile and PC devices with specific dimensions:
- **PC Banner**: 1920×620 pixels
- **Mobile Banner**: 1440×630 pixels

## Changes Made

### 1. Database Schema Update
- Added `mobile_image` column to `hero_slider` table
- Updated `HeroSlider` model in `models.py`

### 2. Admin Interface Enhancement
- Updated `HeroSliderForm` in `forms.py` to include mobile image upload
- Enhanced admin template (`templates/admin_hero_slider.html`) with:
  - Separate upload fields for PC and mobile images
  - Image size recommendations
  - Preview of both images in the management interface

### 3. Frontend Responsive Implementation
- Updated homepage template (`templates/index.html`) with:
  - Responsive image display using Bootstrap classes
  - PC images shown on desktop (`d-none d-md-block`)
  - Mobile images shown on mobile (`d-block d-md-none`)
  - Fallback to PC image if mobile image not available

### 4. CSS Responsive Styling
- Added specific CSS rules for banner dimensions:
  - PC: Fixed height of 620px
  - Mobile: Fixed height of 630px
  - Tablet: Adjusted height of 500px
  - Small mobile: Reduced height of 400px

### 5. Backend Route Updates
- Updated `admin_hero_slider()` route to handle both image uploads
- Enhanced `delete_hero_slide()` route to remove both image files
- Added automatic filename suffixing for mobile images (`_mobile`)

## File Changes

### Modified Files:
1. `models.py` - Added mobile_image column
2. `forms.py` - Updated HeroSliderForm
3. `app.py` - Updated hero slider routes
4. `templates/admin_hero_slider.html` - Enhanced admin interface
5. `templates/index.html` - Added responsive image display

### New Files:
1. `update_hero_slider_db.py` - Database migration script
2. `BANNER_RESPONSIVE_UPDATE_README.md` - This documentation

## Installation Instructions

### For Existing Installations:
1. Run the database migration script:
   ```bash
   python3 update_hero_slider_db.py
   ```

2. Restart your Flask application

3. Access the admin panel at `/admin/hero-slider` to upload new banners

### For New Installations:
The database schema will be created automatically with the mobile_image column included.

## Usage Instructions

### Admin Panel:
1. Navigate to `/admin/hero-slider`
2. Fill in the slide details (title, description, button text/URL)
3. Upload PC image (recommended: 1920×620 pixels)
4. Upload mobile image (recommended: 1440×630 pixels)
5. Click "Save" to create the slide

### Image Requirements:
- **PC Image**: 1920×620 pixels (aspect ratio 3.1:1)
- **Mobile Image**: 1440×630 pixels (aspect ratio 2.3:1)
- Supported formats: JPG, JPEG, PNG
- Images will be automatically resized to fit containers while maintaining aspect ratio

### Responsive Behavior:
- Desktop/Tablet (≥768px): Shows PC image
- Mobile (<768px): Shows mobile image
- Fallback: If no mobile image, PC image is used on mobile
- Object-fit: cover ensures images fill containers properly

## Technical Details

### CSS Media Queries:
```css
/* PC Banner */
@media (min-width: 768px) {
  .banner-container { height: 620px; }
}

/* Mobile Banner */
@media (max-width: 767px) {
  .banner-container { height: 630px; }
}
```

### Bootstrap Classes Used:
- `d-none d-md-block` - Hide on mobile, show on desktop
- `d-block d-md-none` - Show on mobile, hide on desktop

### File Naming Convention:
- PC images: `original_filename.ext`
- Mobile images: `original_filename_mobile.ext`

## Troubleshooting

### Common Issues:
1. **Images not displaying**: Check file permissions in `static/images/` folder
2. **Database error**: Ensure migration script ran successfully
3. **Responsive not working**: Clear browser cache and check CSS

### Verification Steps:
1. Check database has `mobile_image` column: `sqlite3 instance/site.db ".schema hero_slider"`
2. Verify images uploaded to `static/images/` folder
3. Test responsive behavior using browser dev tools

## Future Enhancements
- Image compression/optimization
- Drag-and-drop upload interface
- Bulk image management
- Image cropping tools
- WebP format support

## Support
For issues or questions, check the application logs and ensure all dependencies are properly installed.