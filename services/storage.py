# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የፋይል ማከማቻ አገልግሎት
ይህ ፋይል የፋይል ማከማቻ ተዛማጅ አገልግሎቶችን ይይዛል
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, BinaryIO
import hashlib
import base64

from config import config
from utils.logger import get_logger

logger = get_logger('storage')


class StorageService:
    """የፋይል ማከማቻ አገልግሎት ክፍል"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.assets_dir = self.base_dir / 'assets'
        self.images_dir = self.assets_dir / 'images'
        self.documents_dir = self.assets_dir / 'documents'
        self.temp_dir = self.assets_dir / 'temp'
        
        # ማውጫዎችን መፍጠር
        for dir_path in [self.assets_dir, self.images_dir, self.documents_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # ንዑስ ማውጫዎች
        self.product_images_dir = self.images_dir / 'products'
        self.user_images_dir = self.images_dir / 'users'
        self.system_images_dir = self.images_dir / 'system'
        self.invoices_dir = self.documents_dir / 'invoices'
        self.backups_dir = self.documents_dir / 'backups'
        
        for dir_path in [self.product_images_dir, self.user_images_dir, 
                         self.system_images_dir, self.invoices_dir, self.backups_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("✅ የፋይል ማከማቻ አገልግሎት ተዘጋጅቷል")
    
    # ==================== ፋይል ማስቀመጥ ====================
    
    def save_file(self, file_data: bytes, filename: str, 
                  subdir: str = 'temp') -> Optional[str]:
        """ፋይል ማስቀመጥ"""
        try:
            # ማውጫ መምረጥ
            if subdir == 'products':
                save_dir = self.product_images_dir
            elif subdir == 'users':
                save_dir = self.user_images_dir
            elif subdir == 'system':
                save_dir = self.system_images_dir
            elif subdir == 'invoices':
                save_dir = self.invoices_dir
            elif subdir == 'backups':
                save_dir = self.backups_dir
            else:
                save_dir = self.temp_dir
            
            # ፋይል ስም ማፍጠር
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            safe_name = f"{name}_{timestamp}{ext}"
            file_path = save_dir / safe_name
            
            # ፋይል ማስቀመጥ
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # አንጻራዊ መንገድ መመለስ
            relative_path = str(file_path.relative_to(self.base_dir))
            logger.info(f"✅ ፋይል ተቀምጧል: {relative_path}")
            
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ ፋይል ማስቀመጥ አልተቻለም: {e}")
            return None
    
    def save_image(self, image_data: bytes, filename: str, 
                   subdir: str = 'products') -> Optional[str]:
        """ምስል ማስቀመጥ"""
        return self.save_file(image_data, filename, subdir)
    
    def save_text_file(self, content: str, filename: str, 
                       subdir: str = 'temp') -> Optional[str]:
        """የጽሁፍ ፋይል ማስቀመጥ"""
        try:
            file_data = content.encode('utf-8')
            return self.save_file(file_data, filename, subdir)
        except Exception as e:
            logger.error(f"❌ የጽሁፍ ፋይል ማስቀመጥ አልተቻለም: {e}")
            return None
    
    def save_json_file(self, data: Dict, filename: str, 
                       subdir: str = 'temp') -> Optional[str]:
        """JSON ፋይል ማስቀመጥ"""
        try:
            content = json.dumps(data, ensure_ascii=False, indent=2)
            return self.save_text_file(content, filename, subdir)
        except Exception as e:
            logger.error(f"❌ JSON ፋይል ማስቀመጥ አልተቻለም: {e}")
            return None
    
    # ==================== ፋይል ማንበብ ====================
    
    def read_file(self, filepath: str) -> Optional[bytes]:
        """ፋይል ማንበብ"""
        try:
            full_path = self.base_dir / filepath
            
            if not full_path.exists():
                logger.warning(f"⚠️ ፋይል አልተገኘም: {filepath}")
                return None
            
            with open(full_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"❌ ፋይል ማንበብ አልተቻለም: {e}")
            return None
    
    def read_text_file(self, filepath: str) -> Optional[str]:
        """የጽሁፍ ፋይል ማንበብ"""
        try:
            data = self.read_file(filepath)
            return data.decode('utf-8') if data else None
        except Exception as e:
            logger.error(f"❌ የጽሁፍ ፋይል ማንበብ አልተቻለም: {e}")
            return None
    
    def read_json_file(self, filepath: str) -> Optional[Dict]:
        """JSON ፋይል ማንበብ"""
        try:
            content = self.read_text_file(filepath)
            return json.loads(content) if content else None
        except Exception as e:
            logger.error(f"❌ JSON ፋይል ማንበብ አልተቻለም: {e}")
            return None
    
    # ==================== ፋይል መሰረዝ ====================
    
    def delete_file(self, filepath: str) -> bool:
        """ፋይል መሰረዝ"""
        try:
            full_path = self.base_dir / filepath
            
            if not full_path.exists():
                return True
            
            full_path.unlink()
            logger.info(f"✅ ፋይል ተሰርዟል: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ፋይል መሰረዝ አልተቻለም: {e}")
            return False
    
    def delete_directory(self, dirpath: str) -> bool:
        """ማውጫ መሰረዝ"""
        try:
            full_path = self.base_dir / dirpath
            
            if not full_path.exists():
                return True
            
            shutil.rmtree(full_path)
            logger.info(f"✅ ማውጫ ተሰርዟል: {dirpath}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ማውጫ መሰረዝ አልተቻለም: {e}")
            return False
    
    # ==================== ፋይል መንቀሳቀስ ====================
    
    def move_file(self, source: str, destination: str) -> bool:
        """ፋይል መንቀሳቀስ"""
        try:
            src_path = self.base_dir / source
            dst_path = self.base_dir / destination
            
            if not src_path.exists():
                return False
            
            # ማውጫ መፍጠር
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src_path), str(dst_path))
            logger.info(f"✅ ፋይል ተንቀሳቅሷል: {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ፋይል መንቀሳቀስ አልተቻለም: {e}")
            return False
    
    def copy_file(self, source: str, destination: str) -> bool:
        """ፋይል መቅዳት"""
        try:
            src_path = self.base_dir / source
            dst_path = self.base_dir / destination
            
            if not src_path.exists():
                return False
            
            # ማውጫ መፍጠር
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(str(src_path), str(dst_path))
            logger.info(f"✅ ፋይል ተቀድቷል: {source} -> {destination}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ፋይል መቅዳት አልተቻለም: {e}")
            return False
    
    # ==================== ፋይል መረጃ ====================
    
    def get_file_info(self, filepath: str) -> Optional[Dict]:
        """የፋይል መረጃ ማግኘት"""
        try:
            full_path = self.base_dir / filepath
            
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            
            return {
                'name': full_path.name,
                'path': str(filepath),
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'is_file': full_path.is_file(),
                'extension': full_path.suffix,
                'parent': str(full_path.parent.relative_to(self.base_dir))
            }
            
        except Exception as e:
            logger.error(f"❌ የፋይል መረጃ ማግኘት አልተቻለም: {e}")
            return None
    
    def list_files(self, subdir: str = 'temp', pattern: str = '*') -> List[Dict]:
        """ፋይሎችን መዘርዘር"""
        try:
            if subdir == 'products':
                search_dir = self.product_images_dir
            elif subdir == 'users':
                search_dir = self.user_images_dir
            elif subdir == 'system':
                search_dir = self.system_images_dir
            elif subdir == 'invoices':
                search_dir = self.invoices_dir
            elif subdir == 'backups':
                search_dir = self.backups_dir
            else:
                search_dir = self.temp_dir
            
            files = []
            for file_path in search_dir.glob(pattern):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(self.base_dir))
                    info = self.get_file_info(relative_path)
                    if info:
                        files.append(info)
            
            return sorted(files, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ ፋይሎችን መዘርዘር አልተቻለም: {e}")
            return []
    
    # ==================== ምትኬ ====================
    
    def create_backup(self, name: str = None) -> Optional[str]:
        """የውሂብ ጎታ ምትኬ መፍጠር"""
        try:
            if not name:
                name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # የውሂብ ጎታ ፋይል
            db_path = self.base_dir / config.database.DB_PATH
            
            if not db_path.exists():
                logger.error("❌ የውሂብ ጎታ ፋይል አልተገኘም")
                return None
            
            # ምትኬ ማውጫ
            backup_dir = self.backups_dir / name
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # የውሂብ ጎታ መቅዳት
            backup_db = backup_dir / 'zenach.db'
            shutil.copy2(str(db_path), str(backup_db))
            
            # ምትኬ መረጃ መፍጠር
            backup_info = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'db_size': db_path.stat().st_size,
                'files': []
            }
            
            # ሌሎች ፋይሎች መቅዳት
            for dir_name in ['assets', 'cache', 'logs']:
                src_dir = self.base_dir / dir_name
                if src_dir.exists():
                    dst_dir = backup_dir / dir_name
                    shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            
            # መረጃ ማስቀመጥ
            info_path = backup_dir / 'backup_info.json'
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)
            
            relative_path = str(backup_dir.relative_to(self.base_dir))
            logger.info(f"✅ ምትኬ ተፈጥሯል: {relative_path}")
            
            return relative_path
            
        except Exception as e:
            logger.error(f"❌ ምትኬ መፍጠር አልተቻለም: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """ምትኬ መመለስ"""
        try:
            full_path = self.base_dir / backup_path
            
            if not full_path.exists():
                logger.error(f"❌ ምትኬ አልተገኘም: {backup_path}")
                return False
            
            # የውሂብ ጎታ መመለስ
            backup_db = full_path / 'zenach.db'
            if backup_db.exists():
                db_path = self.base_dir / config.database.DB_PATH
                shutil.copy2(str(backup_db), str(db_path))
            
            # ሌሎች ፋይሎች መመለስ
            for dir_name in ['assets', 'cache', 'logs']:
                src_dir = full_path / dir_name
                if src_dir.exists():
                    dst_dir = self.base_dir / dir_name
                    shutil.copytree(str(src_dir), str(dst_dir), dirs_exist_ok=True)
            
            logger.info(f"✅ ምትኬ ተመልሷል: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ምትኬ መመለስ አልተቻለም: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """ምትኬዎችን መዘርዘር"""
        try:
            backups = []
            
            for backup_dir in self.backups_dir.iterdir():
                if backup_dir.is_dir():
                    info_path = backup_dir / 'backup_info.json'
                    
                    if info_path.exists():
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                    else:
                        info = {
                            'name': backup_dir.name,
                            'created_at': datetime.fromtimestamp(
                                backup_dir.stat().st_mtime
                            ).isoformat()
                        }
                    
                    info['path'] = str(backup_dir.relative_to(self.base_dir))
                    backups.append(info)
            
            return sorted(backups, key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ ምትኬዎችን መዘርዘር አልተቻለም: {e}")
            return []
    
    def delete_backup(self, backup_path: str) -> bool:
        """ምትኬ መሰረዝ"""
        try:
            full_path = self.base_dir / backup_path
            
            if not full_path.exists():
                return True
            
            shutil.rmtree(full_path)
            logger.info(f"✅ ምትኬ ተሰርዟል: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ ምትኬ መሰረዝ አልተቻለም: {e}")
            return False
    
    # ==================== ማጽዳት ====================
    
    def clean_temp_files(self, days: int = 7) -> int:
        """ጊዜያዊ ፋይሎችን ማጽዳት"""
        try:
            count = 0
            now = datetime.now()
            
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if (now - mtime).days > days:
                        file_path.unlink()
                        count += 1
            
            logger.info(f"✅ {count} ጊዜያዊ ፋይሎች ተጽድተዋል")
            return count
            
        except Exception as e:
            logger.error(f"❌ ጊዜያዊ ፋይሎችን ማጽዳት አልተቻለም: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict:
        """የማከማቻ ስታቲስቲክስ"""
        try:
            stats = {
                'total_size': 0,
                'files_count': 0,
                'directories': {}
            }
            
            for dir_name in ['images', 'documents', 'temp']:
                dir_path = self.assets_dir / dir_name
                if dir_path.exists():
                    size = 0
                    count = 0
                    
                    for file_path in dir_path.glob('**/*'):
                        if file_path.is_file():
                            size += file_path.stat().st_size
                            count += 1
                    
                    stats['directories'][dir_name] = {
                        'size': size,
                        'files': count
                    }
                    stats['total_size'] += size
                    stats['files_count'] += count
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ የማከማቻ ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {'total_size': 0, 'files_count': 0, 'directories': {}}