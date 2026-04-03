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
                except (OSError, PermissionError) as e:
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
                except (OSError, PermissionError):
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
                except (OSError, PermissionError):
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


    async def ai_cleanup_analysis(self, 
                                   folder: str) -> dict:
        """AI-powered cleanup analysis. Returns a 
        report dict without executing anything."""
        import os, hashlib, httpx
        from datetime import datetime, timedelta
        
        folder = os.path.expanduser(folder)
        if not os.path.exists(folder):
            return {"error": f"Folder not found: {folder}"}
        
        print(f"[FileManager] Analyzing {folder}...")
        
        # ── SCAN ─────────────────────────────────
        junk = []          # delete these
        to_organize = []   # move to subfolders
        to_archive = []    # move to _archive
        duplicates = []    # duplicate files
        
        JUNK_NAMES = {
            '.DS_Store', 'Thumbs.db', '.localized',
            'desktop.ini', '.Spotlight-V100',
            '.Trashes', '.fseventsd'
        }
        JUNK_EXTENSIONS = {
            '.tmp', '.temp', '.log', '.cache',
            '.bak', '.old', '.orig', '.swp',
            '~'
        }
        ORGANIZE_MAP = {
            'Images': {
                '.jpg','.jpeg','.png','.gif',
                '.webp','.svg','.ico','.heic',
                '.raw','.tiff'
            },
            'Documents': {
                '.pdf','.doc','.docx','.txt',
                '.md','.pages','.rtf','.odt'
            },
            'Spreadsheets': {
                '.xls','.xlsx','.csv','.numbers'
            },
            'Presentations': {
                '.ppt','.pptx','.key'
            },
            'Videos': {
                '.mp4','.mov','.avi','.mkv',
                '.wmv','.flv','.webm'
            },
            'Audio': {
                '.mp3','.wav','.flac','.aac',
                '.m4a','.ogg'
            },
            'Archives': {
                '.zip','.tar','.gz','.rar',
                '.7z','.dmg','.pkg'
            },
            'Code': {
                '.py','.js','.ts','.html',
                '.css','.json','.yaml','.yml',
                '.sh','.bash','.rb','.go',
                '.rs','.cpp','.c','.h'
            },
        }
        
        # Build reverse map: ext -> folder
        ext_to_folder = {}
        for folder_name, exts in ORGANIZE_MAP.items():
            for ext in exts:
                ext_to_folder[ext] = folder_name
        
        # Hash map for duplicate detection
        hashes = {}
        cutoff = datetime.now() - timedelta(days=30)
        
        total_size = 0
        junk_size = 0
        archive_size = 0
        
        try:
            entries = os.listdir(folder)
        except PermissionError:
            return {"error": "Permission denied"}
        
        for fname in entries:
            fpath = os.path.join(folder, fname)
            
            # Skip hidden system files we don't 
            # want to touch
            if fname.startswith('.') and \
               fname not in JUNK_NAMES:
                continue
            
            try:
                stat = os.stat(fpath)
                size_mb = stat.st_size / (1024*1024)
                total_size += size_mb
                mtime = datetime.fromtimestamp(
                    stat.st_mtime
                )
                
                ext = os.path.splitext(fname)[1].lower()
                
                # 1. JUNK CHECK
                if fname in JUNK_NAMES or \
                   ext in JUNK_EXTENSIONS:
                    junk.append({
                        "path": fpath,
                        "name": fname,
                        "size_mb": round(size_mb, 2),
                        "reason": "junk file"
                    })
                    junk_size += size_mb
                    continue
                
                # 2. DUPLICATE CHECK (files only)
                if os.path.isfile(fpath) and \
                   stat.st_size < 100*1024*1024:
                    try:
                        h = hashlib.md5()
                        with open(fpath, 'rb') as f:
                            h.update(f.read(8192))
                        fhash = h.hexdigest()
                        if fhash in hashes:
                            duplicates.append({
                                "path": fpath,
                                "name": fname,
                                "size_mb": round(
                                    size_mb, 2
                                ),
                                "duplicate_of": hashes[
                                    fhash
                                ],
                                "reason": "duplicate"
                            })
                            junk_size += size_mb
                        else:
                            hashes[fhash] = fpath
                    except (OSError, PermissionError):
                        pass
                
                # 3. ARCHIVE CHECK (old files)
                if mtime < cutoff and \
                   os.path.isfile(fpath):
                    days_old = (
                        datetime.now() - mtime
                    ).days
                    to_archive.append({
                        "path": fpath,
                        "name": fname,
                        "size_mb": round(size_mb, 2),
                        "days_old": days_old,
                        "reason": f"not used in "
                                  f"{days_old} days"
                    })
                    archive_size += size_mb
                    continue
                
                # 4. ORGANIZE CHECK
                if os.path.isfile(fpath) and \
                   ext in ext_to_folder:
                    target_folder = ext_to_folder[ext]
                    to_organize.append({
                        "path": fpath,
                        "name": fname,
                        "size_mb": round(size_mb, 2),
                        "move_to": target_folder,
                        "reason": f"belongs in "
                                  f"{target_folder}/"
                    })
            
            except (PermissionError, OSError):
                pass
        
        # ── AI SUMMARY ───────────────────────────
        summary_prompt = (
            f"You are analyzing the folder: {folder}\n"
            f"Files scanned: {len(entries)}\n"
            f"Total size: {round(total_size, 1)} MB\n\n"
            f"Found:\n"
            f"- {len(junk)} junk files "
            f"({round(junk_size,1)} MB)\n"
            f"- {len(duplicates)} duplicates\n"
            f"- {len(to_archive)} old files to archive "
            f"({round(archive_size,1)} MB)\n"
            f"- {len(to_organize)} files to organize\n\n"
            f"Junk examples: "
            f"{[j['name'] for j in junk[:5]]}\n"
            f"Archive examples: "
            f"{[a['name'] for a in to_archive[:5]]}\n\n"
            f"Write a 2-sentence summary of what "
            f"should be done, then list the top 3 "
            f"most impactful actions."
        )
        
        ai_summary = "Analysis complete."
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from llm import _chat
            ai_summary = _chat(
                system="You are an AI assistant analyzing file folders.",
                user=summary_prompt
            )
        except Exception as e:
            print(f"[FileManager] AI cleanup analysis failed: {e}")
            ai_summary = (
                f"Found {len(junk)} junk files, "
                f"{len(duplicates)} duplicates, "
                f"{len(to_archive)} files to archive, "
                f"and {len(to_organize)} files to "
                f"organize. Approve to proceed."
            )
        
        return {
            "folder": folder,
            "total_files": len(entries),
            "total_size_mb": round(total_size, 1),
            "junk": junk,
            "duplicates": duplicates,
            "to_archive": to_archive,
            "to_organize": to_organize,
            "junk_size_mb": round(junk_size, 1),
            "archive_size_mb": round(archive_size, 1),
            "ai_summary": ai_summary,
            "status": "pending_approval"
        }

    async def ai_cleanup_execute(self,
                                  report: dict) -> str:
        """Execute cleanup after user approval."""
        import os, shutil
        from datetime import datetime
        
        folder = report["folder"]
        results = []
        freed_mb = 0
        
        # 1. Delete junk
        for item in report.get("junk", []):
            try:
                if os.path.isfile(item["path"]):
                    os.remove(item["path"])
                elif os.path.isdir(item["path"]):
                    shutil.rmtree(item["path"])
                freed_mb += item.get("size_mb", 0)
                results.append(
                    f"🗑 Deleted: {item['name']}"
                )
            except Exception as e:
                results.append(
                    f"✗ Could not delete "
                    f"{item['name']}: {e}"
                )
        
        # 2. Delete duplicates
        for item in report.get("duplicates", []):
            try:
                os.remove(item["path"])
                freed_mb += item.get("size_mb", 0)
                results.append(
                    f"🗑 Removed duplicate: "
                    f"{item['name']}"
                )
            except Exception as e:
                results.append(
                    f"✗ Could not remove "
                    f"{item['name']}: {e}"
                )
        
        # 3. Archive old files
        archive_dir = os.path.join(
            folder, "_archive"
        )
        os.makedirs(archive_dir, exist_ok=True)
        for item in report.get("to_archive", []):
            try:
                dest = os.path.join(
                    archive_dir, item["name"]
                )
                shutil.move(item["path"], dest)
                results.append(
                    f"📦 Archived: {item['name']} "
                    f"({item['days_old']} days old)"
                )
            except Exception as e:
                results.append(
                    f"✗ Could not archive "
                    f"{item['name']}: {e}"
                )
        
        # 4. Organize files into subfolders
        for item in report.get("to_organize", []):
            try:
                target_dir = os.path.join(
                    folder, item["move_to"]
                )
                os.makedirs(target_dir, exist_ok=True)
                dest = os.path.join(
                    target_dir, item["name"]
                )
                # Handle name conflicts
                if os.path.exists(dest):
                    base, ext = os.path.splitext(
                        item["name"]
                    )
                    dest = os.path.join(
                        target_dir,
                        f"{base}_{datetime.now().strftime('%H%M%S')}{ext}"
                    )
                shutil.move(item["path"], dest)
                results.append(
                    f"📁 Moved: {item['name']} → "
                    f"{item['move_to']}/"
                )
            except Exception as e:
                results.append(
                    f"✗ Could not move "
                    f"{item['name']}: {e}"
                )
        
        summary = (
            f"✅ Cleanup complete!\n"
            f"Freed: {round(freed_mb, 1)} MB\n"
            f"Actions taken: {len(results)}\n\n"
            + "\n".join(results[:20])
        )
        
        if len(results) > 20:
            summary += (
                f"\n... and {len(results)-20} more"
            )
        
        return summary

file_manager = FileManager()
