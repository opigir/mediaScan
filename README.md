# mediaScan
Problem: I have large backups of the raw data from the datawrangling from many video and photo projects, the RAW data is not required as many of those projects have been completed. These files are nested deep within project folders. 

Solution: Scan for large media folders and search for camera folder names to decide if you need to keep it or remove it to clear space. This script WILL NOT DELETE ANY FILES but will allow you to open the folder and manually do so.

# Media Scanner Application Summary (AI generated)

## Overview
This script implements a GUI application for scanning and managing media files (photos and videos) from camera folders. It helps users organize, review, and manage media content across different directories.

## Main Components

### 1. MediaScanner Class
- Scans directories for camera-related folders (DCIM, PRIVATE, etc.)
- Identifies media files (photos, videos, RAW files)
- Calculates folder sizes and gathers media information
- Saves scan results to JSON files
- Supports progress tracking during scans

### 2. ThumbnailGrid Class
- Creates a scrollable grid view for media files
- Displays file icons based on type (📷 for images, 🎥 for videos, etc.)
- Handles thumbnail generation and display
- Supports different file types (images, videos, RAW files)

### 3. MediaManager Class (Main Application)
The core UI component with three main panels:
- Left Panel: Folder list/tree view
- Center Panel: Two modes
  - Scan Mode: For initiating new scans
  - Viewer Mode: Shows thumbnails and folder information
- Right Panel: JSON data display

## Key Features
1. **File Management**
   - Scan directories for media content
   - Load existing scans from JSON
   - Mark folders for deletion or keeping
   - Calculate storage sizes

2. **Navigation**
   - Browse through folders
   - Previous/Next folder navigation
   - Direct folder selection from tree view

3. **Visual Interface**
   - Thumbnail previews of media files
   - Progress tracking for scans
   - File type icons for different media types
   - Folder statistics and information

4. **File Support**
- Photos: .jpg, .jpeg, .cr2, .cr3, .nef, .arw, .raw, .dng
- Videos: .mp4, .mov, .mts, .m2ts, .avi

## Technical Features
- Multi-threaded scanning for responsive UI
- Batch loading of thumbnails for performance
- Error handling and progress tracking
- File system integration for opening folders
- JSON-based data persistence
- Cross-platform support (Windows/macOS/Linux)
