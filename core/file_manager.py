import os
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List

class FileManager:
    
    # ─── BULK OPERATIONS ─────────────────────────
    
    def organize_folder(self, 
                         path: str) -> str:
        """
        Organize folder by file type.
        Creates subfolders: Images, Documents,
        Videos, Audio, Code, Archives, Other
        """
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return f"Folder not found: {path}"
        
        TYPE_MAP = {
            'Images': [
                '.jpg','.jpeg','.png','.gif',
                '.webp','.svg','.heic','.raw'
            ],
            'Documents': [
                '.pdf','.docx','.doc','.xlsx',
                '.xls','.pptx','.ppt','.txt',
                '.md','.csv'
            ],
            'Videos': [
                '.mp4','.mov','.avi','.mkv',
                '.wmv','.flv','.webm'
            ],
            'Audio': [
                '.mp3','.wav','.flac','.aac',
                '.m4a','.ogg'
            ],
            'Code': [
                '.py','.js','.ts','.html',
                '.css','.json','.yaml','.sh',
                '.swift','.kt'
            ],
            'Archives': [
                '.zip','.tar','.gz','.rar',
                '.7z','.dmg'
            ]
        }
        
        moved = 0
        for fname in os.listdir(expanded):
            fpath = os.path.join(expanded, fname)
            if os.path.isdir(fpath):
                continue
            
            ext = Path(fname).suffix.lower()
            dest_folder = 'Other'
            for folder, exts in TYPE_MAP.items():
                if ext in exts:
                    dest_folder = folder
                    break
            
            dest_dir = os.path.join(
                expanded, dest_folder
            )
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(
                fpath,
                os.path.join(dest_dir, fname)
            )
            moved += 1
        
        return (f"Organized {moved} files in "
                f"{path} into subfolders.")
    
    def find_duplicates(self, 
                         path: str) -> list:
        """Find duplicate files by hash."""
        expanded = os.path.expanduser(path)
        hashes = {}
        duplicates = []
        
        for root, dirs, files in os.walk(expanded):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    h = hashlib.md5(
                        open(fpath, 'rb').read()
                    ).hexdigest()
                    if h in hashes:
                        duplicates.append({
                            'original': hashes[h],
                            'duplicate': fpath,
                            'size': os.path.getsize(
                                fpath
                            )
                        })
                    else:
                        hashes[h] = fpath
                except:
                    pass
        
        return duplicates
    
    def batch_rename(self, path: str,
                      pattern: str,
                      replacement: str) -> str:
        """Batch rename files matching pattern."""
        import re
        expanded = os.path.expanduser(path)
        count = 0
        
        for fname in os.listdir(expanded):
            fpath = os.path.join(expanded, fname)
            if os.path.isfile(fpath):
                new_name = re.sub(
                    pattern, replacement, fname
                )
                if new_name != fname:
                    os.rename(
                        fpath,
                        os.path.join(
                            expanded, new_name
                        )
                    )
                    count += 1
        
        return f"Renamed {count} files."
    
    def batch_convert_images(self, 
                              source_dir: str,
                              target_format: str = "png"
                              ) -> str:
        """Convert all images in folder to format."""
        from PIL import Image
        import os
        
        expanded = os.path.expanduser(source_dir)
        converted = 0
        errors = 0
        
        IMAGE_EXTS = [
            '.jpg', '.jpeg', '.png', '.gif',
            '.bmp', '.tiff', '.webp', '.heic'
        ]
        
        for fname in os.listdir(expanded):
            ext = os.path.splitext(fname)[1].lower()
            if ext in IMAGE_EXTS and \
               ext != f'.{target_format}':
                src = os.path.join(expanded, fname)
                dst = os.path.join(
                    expanded,
                    os.path.splitext(fname)[0] +
                    f'.{target_format}'
                )
                try:
                    img = Image.open(src)
                    if target_format == 'jpg':
                        img = img.convert('RGB')
                    img.save(dst)
                    converted += 1
                except Exception as e:
                    errors += 1
        
        return (f"Converted {converted} images to "
                f"{target_format}. {errors} errors.")
    
    def batch_rename_numbered(self,
                               path: str,
                               prefix: str = "file"
                               ) -> str:
        """Rename all files with numbered prefix."""
        expanded = os.path.expanduser(path)
        files = sorted([
            f for f in os.listdir(expanded)
            if os.path.isfile(
                os.path.join(expanded, f)
            )
        ])
        
        for i, fname in enumerate(files, 1):
            ext = os.path.splitext(fname)[1]
            new_name = f"{prefix}_{i:03d}{ext}"
            os.rename(
                os.path.join(expanded, fname),
                os.path.join(expanded, new_name)
            )
        
        return f"Renamed {len(files)} files with "  \
               f"prefix '{prefix}'"
    
    def get_large_files(self, path: str,
                         min_mb: float = 100) -> list:
        """Find files larger than min_mb."""
        expanded = os.path.expanduser(path)
        large = []
        
        for root, dirs, files in os.walk(expanded):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    size_mb = size / 1024 / 1024
                    if size_mb >= min_mb:
                        large.append({
                            "path": fp,
                            "size_mb": round(size_mb, 1),
                            "name": f
                        })
                except:
                    pass
        
        return sorted(
            large, 
            key=lambda x: x["size_mb"],
            reverse=True
        )[:20]

    def get_folder_stats(self, 
                          path: str) -> dict:
        """Get folder size, file count, types."""
        expanded = os.path.expanduser(path)
        total_size = 0
        file_count = 0
        type_counts = {}
        
        for root, dirs, files in os.walk(expanded):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    total_size += size
                    file_count += 1
                    ext = Path(f).suffix.lower()
                    type_counts[ext] = \
                        type_counts.get(ext, 0) + 1
                except:
                    pass
        
        return {
            'path': path,
            'files': file_count,
            'size_mb': round(
                total_size / 1024 / 1024, 2
            ),
            'types': dict(
                sorted(
                    type_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            )
        }
    
    # ─── PDF TOOLS ───────────────────────────────
    
    def merge_pdfs(self, 
                    paths: list,
                    output: str = None) -> str:
        """Merge multiple PDFs into one."""
        import fitz  # PyMuPDF
        
        merged = fitz.open()
        for p in paths:
            expanded = os.path.expanduser(p)
            doc = fitz.open(expanded)
            merged.insert_pdf(doc)
            doc.close()
        
        output = output or \
            "~/Desktop/merged.pdf"
        expanded_out = os.path.expanduser(output)
        merged.save(expanded_out)
        merged.close()
        
        subprocess.Popen(['open', expanded_out])
        return f"PDFs merged: {output}"
    
    def compress_pdf(self, path: str,
                      output: str = None) -> str:
        """Compress PDF file size."""
        import fitz
        expanded = os.path.expanduser(path)
        doc = fitz.open(expanded)
        
        output = output or path.replace(
            '.pdf', '_compressed.pdf'
        )
        expanded_out = os.path.expanduser(output)
        
        doc.save(
            expanded_out,
            garbage=4,
            deflate=True,
            clean=True
        )
        
        orig_size = os.path.getsize(expanded)
        new_size = os.path.getsize(expanded_out)
        reduction = int(
            (1 - new_size/orig_size) * 100
        )
        
        return (f"PDF compressed. "
                f"Reduced by {reduction}%: "
                f"{output}")
    
    def pdf_to_text(self, path: str) -> str:
        """Extract text from PDF."""
        import fitz
        expanded = os.path.expanduser(path)
        doc = fitz.open(expanded)
        text = ""
        for page in doc:
            text += page.get_text()
        return text[:5000]
    
    def split_pdf(self, path: str,
                   pages: str = None) -> str:
        """Split PDF — pages='1-3' or '1,2,5'"""
        import fitz
        expanded = os.path.expanduser(path)
        doc = fitz.open(expanded)
        
        new_doc = fitz.open()
        
        if pages:
            if '-' in pages:
                start, end = pages.split('-')
                page_list = list(range(
                    int(start)-1, int(end)
                ))
            else:
                page_list = [
                    int(p)-1 
                    for p in pages.split(',')
                ]
        else:
            page_list = list(range(len(doc)))
        
        new_doc.insert_pdf(
            doc, from_page=page_list[0],
            to_page=page_list[-1]
        )
        
        output = expanded.replace(
            '.pdf', f'_split_{pages}.pdf'
        )
        new_doc.save(output)
        return f"PDF split saved: {output}"

file_manager = FileManager()
