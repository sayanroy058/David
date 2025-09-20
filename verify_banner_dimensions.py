#!/usr/bin/env python3
"""
Verification script to check banner dimensions implementation
"""

import re
import os

def check_css_dimensions():
    """Check if the CSS has the correct banner dimensions"""
    print("🔍 Checking CSS banner dimensions...")
    
    with open('templates/index.html', 'r') as f:
        content = f.read()
    
    # Check for PC dimensions (1920×620)
    pc_height_pattern = r'height:\s*620px'
    pc_width_pattern = r'max-width:\s*1920px'
    pc_aspect_pattern = r'aspect-ratio:\s*1920/620'
    
    # Check for Mobile dimensions (1440×630)
    mobile_height_pattern = r'height:\s*630px'
    mobile_width_pattern = r'max-width:\s*1440px'
    mobile_aspect_pattern = r'aspect-ratio:\s*1440/630'
    
    checks = [
        ("PC height (620px)", pc_height_pattern),
        ("PC max-width (1920px)", pc_width_pattern),
        ("PC aspect ratio (1920/620)", pc_aspect_pattern),
        ("Mobile height (630px)", mobile_height_pattern),
        ("Mobile max-width (1440px)", mobile_width_pattern),
        ("Mobile aspect ratio (1440/630)", mobile_aspect_pattern),
    ]
    
    all_passed = True
    for check_name, pattern in checks:
        if re.search(pattern, content):
            print(f"✅ {check_name} - Found")
        else:
            print(f"❌ {check_name} - Missing")
            all_passed = False
    
    return all_passed

def check_responsive_classes():
    """Check if responsive Bootstrap classes are properly implemented"""
    print("\n🔍 Checking responsive Bootstrap classes...")
    
    with open('templates/index.html', 'r') as f:
        content = f.read()
    
    # Check for responsive classes
    responsive_checks = [
        ("PC image visibility", r'd-none d-md-block'),
        ("Mobile image visibility", r'd-block d-md-none'),
        ("PC media query", r'@media \(min-width: 768px\)'),
        ("Mobile media query", r'@media \(max-width: 767px\)'),
    ]
    
    all_passed = True
    for check_name, pattern in responsive_checks:
        if re.search(pattern, content):
            print(f"✅ {check_name} - Found")
        else:
            print(f"❌ {check_name} - Missing")
            all_passed = False
    
    return all_passed

def check_admin_form():
    """Check if admin form has correct dimension labels"""
    print("\n🔍 Checking admin form labels...")
    
    with open('forms.py', 'r') as f:
        content = f.read()
    
    form_checks = [
        ("PC image label", r'PC Image \(1920×620\)'),
        ("Mobile image label", r'Mobile Image \(1440×630\)'),
    ]
    
    all_passed = True
    for check_name, pattern in form_checks:
        if re.search(pattern, content):
            print(f"✅ {check_name} - Found")
        else:
            print(f"❌ {check_name} - Missing")
            all_passed = False
    
    return all_passed

def main():
    print("🔄 Verifying banner dimensions implementation...")
    print("=" * 50)
    
    css_ok = check_css_dimensions()
    responsive_ok = check_responsive_classes()
    form_ok = check_admin_form()
    
    print("\n" + "=" * 50)
    
    if css_ok and responsive_ok and form_ok:
        print("🎉 All banner dimension checks PASSED!")
        print("\n📏 Banner Specifications:")
        print("   • PC: 1920×620 pixels (aspect ratio 3.1:1)")
        print("   • Mobile: 1440×630 pixels (aspect ratio 2.3:1)")
        print("\n🖥️  Desktop (≥768px): Shows PC image")
        print("📱 Mobile (<768px): Shows mobile image")
        print("\n✨ Implementation is ready for use!")
    else:
        print("❌ Some banner dimension checks FAILED!")
        print("Please review the errors above and fix them.")

if __name__ == '__main__':
    main()