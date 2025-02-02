import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from PIL import Image, ImageTk
import datetime
from typing import Dict, List
import subprocess
from tkinter import Canvas, Scrollbar
import threading
from queue import Queue

class MediaScanner:
    def __init__(self, base_path: str, output_file: str):
        self.base_path = os.path.normpath(base_path)
        self.output_file = output_file
        self.camera_folder_patterns = [
            'DCIM',
            'PRIVATE',
            '100EOS',
            '101EOS',
            '102EOS',
            'CANON',
            'SD_VIDEO',
            'AVCHD',
        ]
        self.media_extensions = {
            'photos': {'.jpg', '.jpeg', '.cr2', '.cr3', '.nef', '.arw', '.raw', '.dng'},
            'videos': {'.mp4', '.mov', '.mts', '.m2ts', '.avi'}
        }
        
    def scan_and_save(self, progress_callback=None) -> Dict:
        try:
            scan_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            results = {
                'scan_time': scan_time,
                'base_path': self.base_path,
                'total_size_mb': 0,
                'folders': []
            }

            # First, count total folders for progress
            total_folders = sum(1 for _ in os.walk(self.base_path))
            processed_folders = 0

            for root, dirs, _ in os.walk(self.base_path):
                processed_folders += 1
                if progress_callback:
                    progress = (processed_folders / total_folders) * 100
                    progress_callback(progress)

                for dir_name in dirs:
                    try:
                        full_path = os.path.normpath(os.path.join(root, dir_name))
                        
                        if self.is_camera_folder(dir_name) and self.contains_media_files(full_path):
                            size_mb = self.get_folder_size(full_path)
                            media_info = self.get_media_info(full_path)
                            
                            folder_info = {
                                'name': dir_name,
                                'path': full_path.replace('\\', '\\\\'),
                                'relative_path': os.path.relpath(full_path, self.base_path).replace('\\', '\\\\'),
                                'size_mb': size_mb,
                                'last_modified': datetime.datetime.fromtimestamp(
                                    os.path.getmtime(full_path)
                                ).strftime('%Y-%m-%d %H:%M:%S'),
                                'media_info': media_info,
                                'processed': False,
                                'project_name': os.path.basename(os.path.dirname(full_path))
                            }
                            
                            results['folders'].append(folder_info)
                            results['total_size_mb'] += size_mb
                            
                    except Exception as e:
                        print(f"Error processing directory {dir_name}: {str(e)}")
                        continue

            results['folders'].sort(key=lambda x: x['path'].lower())
            results['total_folders'] = len(results['folders'])
            results['total_size_gb'] = round(results['total_size_mb'] / 1024, 2)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            
            return results
            
        except Exception as e:
            print(f"Error during scan: {str(e)}")
            return {}

    def is_camera_folder(self, folder_name: str) -> bool:
        return any(pattern.lower() in folder_name.lower() for pattern in self.camera_folder_patterns)
    
    def contains_media_files(self, folder_path: str) -> bool:
        try:
            all_extensions = self.media_extensions['photos'].union(self.media_extensions['videos'])
            for root, _, files in os.walk(folder_path):
                if any(f.lower().endswith(tuple(all_extensions)) for f in files):
                    return True
            return False
        except Exception as e:
            print(f"Error checking media files in {folder_path}: {str(e)}")
            return False
    
    def get_folder_size(self, folder_path: str) -> float:
        try:
            total_size = 0
            for root, _, files in os.walk(folder_path):
                total_size += sum(
                    os.path.getsize(os.path.join(root, file))
                    for file in files
                )
            return round(total_size / (1024 * 1024), 2)
        except Exception as e:
            print(f"Error calculating size for {folder_path}: {str(e)}")
            return 0.0

    def get_media_info(self, folder_path: str) -> Dict:
        info = {'photos': 0, 'videos': 0, 'total_files': 0, 'extensions': {}}
        try:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    ext = os.path.splitext(file.lower())[1]
                    if ext in self.media_extensions['photos']:
                        info['photos'] += 1
                    elif ext in self.media_extensions['videos']:
                        info['videos'] += 1
                    info['total_files'] += 1
                    info['extensions'][ext] = info['extensions'].get(ext, 0) + 1
        except Exception as e:
            print(f"Error getting media info for {folder_path}: {str(e)}")
        return info
    
class ThumbnailGrid(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.thumbnail_size = 200
        self.padding = 10
        self.thumbnails = []
        self.thumbnail_folders = ['thumbs', '.thumbs', 'Thumbs', '.Thumbnails']
        
        # Define file type icons
        self.file_icons = {
            'image': '📷',
            'video': '🎥',
            'raw': '📸',
            'unknown': '📄'
        }
        
        # Define file extensions for each type
        self.file_types = {
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp'},
            'video': {'.mp4', '.mov', '.avi', '.mts', '.m2ts'},
            'raw': {'.cr2', '.cr3', '.nef', '.arw', '.raw', '.dng'}
        }
        
        self.create_widgets()
        
    def create_widgets(self):
        """Create and setup the UI elements"""
        # Create canvas with scrollbar
        self.canvas = Canvas(self, bg='white')
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure canvas
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create scrollable window
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bind mousewheel
        self.bind_mousewheel()
        
    def bind_mousewheel(self):
        """Bind mousewheel to scrolling"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def clear(self):
        """Clear all thumbnails"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()

    def find_thumbnail(self, image_path):
        """Try to find an existing thumbnail for the image"""
        # Check parent directory for thumbnail folders
        parent_dir = os.path.dirname(image_path)
        filename = os.path.basename(image_path)
        
        # Look for thumbnails in common thumbnail directories
        for thumb_dir in self.thumbnail_folders:
            thumb_path = os.path.join(parent_dir, thumb_dir, filename)
            if os.path.exists(thumb_path):
                return thumb_path
                
        return None

    def get_file_type(self, filename):
        """Determine file type based on extension"""
        ext = os.path.splitext(filename.lower())[1]
        for ftype, extensions in self.file_types.items():
            if ext in extensions:
                return ftype
        return 'unknown'

    def add_thumbnail(self, file_path, row, col):
        """Add a thumbnail or filename to the grid"""
        try:
            thumb_frame = ttk.Frame(self.scrollable_frame)
            thumb_frame.grid(row=row, column=col, padx=5, pady=5)
            
            # Get file type and corresponding icon
            file_type = self.get_file_type(file_path)
            icon = self.file_icons.get(file_type, self.file_icons['unknown'])
            
            # Create placeholder with icon
            placeholder = ttk.Frame(thumb_frame, width=self.thumbnail_size, height=100)
            placeholder.pack()
            placeholder.pack_propagate(False)
            
            icon_label = ttk.Label(placeholder, text=icon, font=('Arial', 24))
            icon_label.pack(pady=10)
            
            # Show filename and extension
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].upper()
            name_label = ttk.Label(thumb_frame, 
                                 text=f"{filename}\n{ext}",
                                 wraplength=self.thumbnail_size)
            name_label.pack()
            
        except Exception as e:
            print(f"Error creating thumbnail for {file_path}: {str(e)}")

class MediaManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Media Manager")
        self.root.geometry("1400x900")
        
        self.current_folder_index = 0
        self.file_list = []
        self.status_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.scanning = False
        
        self.setup_ui()

    def setup_ui(self):
        # Main container
        self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel for folder list
        self.folder_list_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(self.folder_list_frame, weight=1)

        # Center panel container
        self.center_container = ttk.Frame(self.main_frame)
        self.main_frame.add(self.center_container, weight=3)

        # Right panel for JSON data
        self.right_panel = ttk.Frame(self.main_frame)
        self.main_frame.add(self.right_panel, weight=1)

        # Setup folder list (left panel)
        folder_list_label = ttk.Label(self.folder_list_frame, text="Folders", font=('Arial', 11, 'bold'))
        folder_list_label.pack(pady=5, padx=5, anchor='w')

        self.folder_list = ttk.Treeview(self.folder_list_frame, selectmode='browse', show='tree')
        folder_list_scroll = ttk.Scrollbar(self.folder_list_frame, orient="vertical", command=self.folder_list.yview)
        self.folder_list.configure(yscrollcommand=folder_list_scroll.set)

        folder_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.folder_list.bind('<<TreeviewSelect>>', self.on_folder_select)

        # Setup JSON display (right panel)
        json_label = ttk.Label(self.right_panel, text="Folder Data:", font=('Arial', 11, 'bold'))
        json_label.pack(pady=5, padx=5, anchor='w')
        
        json_frame = ttk.Frame(self.right_panel)
        json_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.json_text = tk.Text(json_frame, wrap=tk.WORD, width=40)
        json_scrollbar = ttk.Scrollbar(json_frame, command=self.json_text.yview)
        self.json_text.configure(yscrollcommand=json_scrollbar.set)
        
        json_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.json_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create both frames in center container
        self.setup_scan_frame()
        self.setup_viewer_frame()
        
        # Initially show scan frame
        self.show_scan_frame()

    def setup_scan_frame(self):
        """Create the scan frame"""
        self.scan_frame = ttk.Frame(self.center_container)
        
        scan_label = ttk.Label(self.scan_frame, 
                             text="Select a folder to scan or load existing scan",
                             font=('Arial', 12))
        scan_label.pack(pady=20)
        
        button_frame = ttk.Frame(self.scan_frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="New Scan", 
                  command=self.select_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Existing Scan", 
                  command=self.load_existing_scan).pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(self.scan_frame, 
                                          variable=self.progress_var,
                                          mode='determinate')
        self.progress_bar.pack(fill=tk.X, padx=50, pady=10)

    def setup_viewer_frame(self):
        """Create the viewer frame"""
        self.viewer_frame = ttk.Frame(self.center_container)
        
        nav_frame = ttk.Frame(self.viewer_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(nav_frame, text="Previous Folder", command=self.prev_folder).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="Next Folder", command=self.next_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_frame, text="New Scan", command=self.new_scan).pack(side=tk.LEFT, padx=5)
        
        info_frame = ttk.Frame(self.viewer_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.folder_info = ttk.Label(info_frame, text="", wraplength=1300)
        self.folder_info.pack(fill=tk.X)

        self.thumbnail_grid = ThumbnailGrid(self.viewer_frame)
        self.thumbnail_grid.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.Frame(self.viewer_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="Mark for Deletion", 
                  command=self.mark_deletion).pack(side=tk.LEFT)
        ttk.Button(control_frame, text="Mark as Keep", 
                  command=self.mark_keep).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Open Folder", 
                  command=self.open_folder).pack(side=tk.LEFT, padx=5)
        
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.RIGHT)

    def show_scan_frame(self):
        """Switch to scan frame"""
        self.viewer_frame.pack_forget()
        self.scan_frame.pack(fill=tk.BOTH, expand=True)
        self.progress_var.set(0)
        
    def show_viewer_frame(self):
        """Switch to viewer frame"""
        self.scan_frame.pack_forget()
        self.viewer_frame.pack(fill=tk.BOTH, expand=True)

    def scanning_complete(self):
        self.scanning = False
        if self.data and self.data.get('folders'):
            self.show_viewer_frame()
            self.load_current_folder()
        else:
            messagebox.showwarning("No Results", 
                                 "No camera media folders found in the selected directory.")

    def new_scan(self):
        self.show_scan_frame()
        
    def load_existing_scan(self):
        """Load a previously saved JSON scan file"""
        json_file = filedialog.askopenfilename(
            title="Select Scan File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if json_file:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                self.data['json_path'] = json_file
                self.show_viewer_frame()
                self.load_current_folder()
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not load scan file: {str(e)}")

# class MediaManager:
#     def __init__(self, root):
#         self.root = root
#         self.root.title("Media Manager")
#         self.root.geometry("1400x900")
        
#         self.current_folder_index = 0
#         self.file_list = []  # Changed from image_list to file_list
#         self.status_var = tk.StringVar()
#         self.progress_var = tk.DoubleVar()
#         self.scanning = False
        
#         self.setup_ui()

#     def setup_ui(self):
#         # Main container
#         self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
#         self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

#         # Left panel for folder list
#         self.folder_list_frame = ttk.Frame(self.main_frame)
#         self.main_frame.add(self.folder_list_frame, weight=1)

#         # Center panel for thumbnails
#         self.center_panel = ttk.Frame(self.main_frame)
#         self.main_frame.add(self.center_panel, weight=3)

#         # Right panel for JSON data
#         self.right_panel = ttk.Frame(self.main_frame)
#         self.main_frame.add(self.right_panel, weight=1)

#         # Initial scan frame (in center panel)
#         self.scan_frame = ttk.Frame(self.center_panel)
#         self.scan_frame.pack(fill=tk.BOTH, expand=True)
        
#         scan_label = ttk.Label(self.scan_frame, 
#                             text="Select a folder to scan or load existing scan",
#                             font=('Arial', 12))
#         scan_label.pack(pady=20)
        
#         # Button frame for scan options
#         button_frame = ttk.Frame(self.scan_frame)
#         button_frame.pack(pady=10)
        
#         ttk.Button(button_frame, text="New Scan", 
#                 command=self.select_folder).pack(side=tk.LEFT, padx=5)
#         ttk.Button(button_frame, text="Load Existing Scan", 
#                 command=self.load_existing_scan).pack(side=tk.LEFT, padx=5)
        
#         self.progress_bar = ttk.Progressbar(self.scan_frame, 
#                                         variable=self.progress_var,
#                                         mode='determinate')
#         self.progress_bar.pack(fill=tk.X, padx=50, pady=10)

#         # Setup folder list
#         folder_list_label = ttk.Label(self.folder_list_frame, text="Folders", font=('Arial', 11, 'bold'))
#         folder_list_label.pack(pady=5, padx=5, anchor='w')

#         # Create Treeview for folder list
#         self.folder_list = ttk.Treeview(self.folder_list_frame, selectmode='browse', show='tree')
#         folder_list_scroll = ttk.Scrollbar(self.folder_list_frame, orient="vertical", command=self.folder_list.yview)
#         self.folder_list.configure(yscrollcommand=folder_list_scroll.set)

#         folder_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
#         self.folder_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

#         # Bind folder selection
#         self.folder_list.bind('<<TreeviewSelect>>', self.on_folder_select)

#         # JSON display in right panel
#         json_label = ttk.Label(self.right_panel, text="Folder Data:", font=('Arial', 11, 'bold'))
#         json_label.pack(pady=5, padx=5, anchor='w')
        
#         # Create Text widget with scrollbar for JSON data
#         json_frame = ttk.Frame(self.right_panel)
#         json_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
#         self.json_text = tk.Text(json_frame, wrap=tk.WORD, width=40)
#         json_scrollbar = ttk.Scrollbar(json_frame, command=self.json_text.yview)
#         self.json_text.configure(yscrollcommand=json_scrollbar.set)
        
#         json_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
#         self.json_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
#         # Viewer frame (initially hidden)
#         self.viewer_frame = ttk.Frame(self.main_frame)
        
#         # Navigation frame
#         nav_frame = ttk.Frame(self.viewer_frame)
#         nav_frame.pack(fill=tk.X, pady=(0, 10))

#         ttk.Button(nav_frame, text="Previous Folder", command=self.prev_folder).pack(side=tk.LEFT)
#         ttk.Button(nav_frame, text="Next Folder", command=self.next_folder).pack(side=tk.LEFT, padx=5)
#         ttk.Button(nav_frame, text="New Scan", command=self.new_scan).pack(side=tk.LEFT, padx=5)
        
#         # Folder info frame
#         info_frame = ttk.Frame(self.viewer_frame)
#         info_frame.pack(fill=tk.X, pady=(0, 10))
        
#         self.folder_info = ttk.Label(info_frame, text="", wraplength=1300)
#         self.folder_info.pack(fill=tk.X)

#         # Thumbnail grid
#         self.thumbnail_grid = ThumbnailGrid(self.viewer_frame)
#         self.thumbnail_grid.pack(fill=tk.BOTH, expand=True)
        
#         # Status and controls
#         control_frame = ttk.Frame(self.viewer_frame)
#         control_frame.pack(fill=tk.X, pady=(10, 0))
        
#         ttk.Button(control_frame, text="Mark for Deletion", 
#                   command=self.mark_deletion).pack(side=tk.LEFT)
#         ttk.Button(control_frame, text="Mark as Keep", 
#                   command=self.mark_keep).pack(side=tk.LEFT, padx=5)
#         ttk.Button(control_frame, text="Open Folder", 
#                   command=self.open_folder).pack(side=tk.LEFT, padx=5)
        
#         self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
#         self.status_label.pack(side=tk.RIGHT)

    def update_folder_list(self):
        """Update the folder list with current data"""
        self.folder_list.delete(*self.folder_list.get_children())
        
        if hasattr(self, 'data') and self.data.get('folders'):
            for idx, folder in enumerate(self.data['folders']):
                # Create folder display text
                folder_text = f"{folder['name']} ({folder['size_mb']:.1f}MB)"
                if folder.get('marked_for_deletion'):
                    folder_text += " [DELETE]"
                
                # Insert into treeview with tag for styling
                tag = 'marked' if folder.get('marked_for_deletion') else ''
                self.folder_list.insert('', 'end', text=folder_text, 
                                    values=(idx,), tags=(tag,))

            # Configure tag colors
            self.folder_list.tag_configure('marked', foreground='red')

            # Select current folder
            items = self.folder_list.get_children()
            if items:
                self.folder_list.selection_set(items[self.current_folder_index])
                self.folder_list.see(items[self.current_folder_index])

    def on_folder_select(self, event):
        """Handle folder selection from the list"""
        selection = self.folder_list.selection()
        if selection:
            item = selection[0]
            idx = int(self.folder_list.item(item)['values'][0])
            if idx != self.current_folder_index:
                self.current_folder_index = idx
                self.load_current_folder()
            
    def load_existing_scan(self):
        """Load a previously saved JSON scan file"""
        json_file = filedialog.askopenfilename(
            title="Select Scan File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if json_file:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                
                # Store the JSON file path for future saves
                self.data['json_path'] = json_file
                
                # Switch to viewer mode
                self.scan_frame.pack_forget()
                self.viewer_frame.pack(fill=tk.BOTH, expand=True)
                self.load_current_folder()
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not load scan file: {str(e)}")
                
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder to Scan")
        if folder_path:
            self.progress_var.set(0)
            self.scanning = True
            
            # Create output filename from folder name
            folder_name = os.path.basename(folder_path)
            output_file = f"{folder_name}_scan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Start scanning in a separate thread
            scanner = MediaScanner(folder_path, output_file)
            
            def scan_thread():
                self.data = scanner.scan_and_save(self.update_progress)
                self.root.after(0, self.scanning_complete)
            
            threading.Thread(target=scan_thread, daemon=True).start()

    def update_progress(self, value):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def scanning_complete(self):
        self.scanning = False
        if self.data and self.data.get('folders'):
            self.scan_frame.pack_forget()
            self.viewer_frame.pack(fill=tk.BOTH, expand=True)
            self.load_current_folder()
        else:
            messagebox.showwarning("No Results", 
                                 "No camera media folders found in the selected directory.")

    def new_scan(self):
        self.viewer_frame.pack_forget()
        self.scan_frame.pack(fill=tk.BOTH, expand=True)
        self.progress_var.set(0)
        
    def load_current_folder(self):
        if not self.data['folders']:
            messagebox.showerror("Error", "No folders found in scan results")
            return

        folder_data = self.data['folders'][self.current_folder_index]
        folder_path = folder_data['path'].replace('\\\\', '\\')

        # Update JSON display
        self.json_text.delete(1.0, tk.END)
        json_str = json.dumps(folder_data, indent=2)
        self.json_text.insert(tk.END, json_str)
        
        self.folder_info.config(text=f"Folder: {folder_data['name']}\n"
                                   f"Project: {folder_data['project_name']}\n"
                                   f"Path: {folder_path}\n"
                                   f"Size: {folder_data['size_mb']:.2f} MB\n"
                                   f"Photos: {folder_data['media_info']['photos']}, "
                                   f"Videos: {folder_data['media_info']['videos']}\n"
                                   f"Status: {'Marked for deletion' if folder_data.get('marked_for_deletion') else 'Keep'}")
        
        self.thumbnail_grid.clear()
        
        # Collect all media files
        self.file_list = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file.lower())[1]
                if (ext in self.thumbnail_grid.file_types['image'] or
                    ext in self.thumbnail_grid.file_types['video'] or
                    ext in self.thumbnail_grid.file_types['raw']):
                    self.file_list.append(os.path.join(root, file))
        
        # Load files in batches
        self.load_file_batch(0)
        
        total_folders = len(self.data['folders'])
        self.status_var.set(f"Folder {self.current_folder_index + 1} of {total_folders}")
        self.update_folder_list()

    def load_file_batch(self, start_index, batch_size=20):
        """Load files in smaller batches"""
        columns = 4
        end_index = min(start_index + batch_size, len(self.file_list))
        
        for idx in range(start_index, end_index):
            row = idx // columns
            col = idx % columns
            self.thumbnail_grid.add_thumbnail(self.file_list[idx], row, col)
            
        # Schedule next batch if there are more files
        if end_index < len(self.file_list):
            self.root.after(100, lambda: self.load_file_batch(end_index))


    def prev_folder(self):
        if self.current_folder_index > 0:
            self.current_folder_index -= 1
            self.load_current_folder()

    def next_folder(self):
        if self.current_folder_index < len(self.data['folders']) - 1:
            self.current_folder_index += 1
            self.load_current_folder()

    def mark_deletion(self):
        self.data['folders'][self.current_folder_index]['marked_for_deletion'] = True
        self.save_json()
        self.load_current_folder()

    def mark_keep(self):
        self.data['folders'][self.current_folder_index]['marked_for_deletion'] = False
        self.save_json()
        self.load_current_folder()

    def open_folder(self):
        folder_path = self.data['folders'][self.current_folder_index]['path'].replace('\\\\', '\\')
        try:
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['xdg-open' if os.name == 'posix' else 'open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {str(e)}")

    def save_json(self):
        try:
            # Save to the original scan file to maintain history
            if hasattr(self, 'data') and 'json_path' in self.data:
                with open(self.data['json_path'], 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save changes: {str(e)}")

def main():
    root = tk.Tk()
    app = MediaManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()