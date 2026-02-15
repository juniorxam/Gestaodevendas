"""
backup.py - Sistema de backup automático do banco de dados
"""

import os
import shutil
import sqlite3
import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Callable
from pathlib import Path

from config import CONFIG


class BackupManager:
    """
    Gerenciador de backups automáticos do banco de dados
    """
    
    def __init__(self, db_path: str, backup_dir: str = "backups"):
        """
        Inicializa o gerenciador de backups
        
        Args:
            db_path: Caminho do arquivo do banco de dados
            backup_dir: Diretório onde os backups serão armazenados
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_thread = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
        # Criar diretório de backups se não existir
        os.makedirs(backup_dir, exist_ok=True)
        
        # Configurar logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Configura logging específico para backups"""
        handler = logging.FileHandler(os.path.join(self.backup_dir, 'backup.log'))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def create_backup(self, suffix: str = "") -> Optional[str]:
        """
        Cria um backup do banco de dados
        
        Args:
            suffix: Sufixo opcional para o nome do arquivo
            
        Returns:
            Caminho do arquivo de backup ou None em caso de erro
        """
        try:
            # Verificar se o banco de dados existe
            if not os.path.exists(self.db_path):
                self.logger.error(f"Banco de dados não encontrado: {self.db_path}")
                return None
            
            # Gerar nome do arquivo de backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix_part = f"_{suffix}" if suffix else ""
            backup_filename = f"backup_{timestamp}{suffix_part}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Criar backup usando a API de backup do SQLite
            self._backup_sqlite(backup_path)
            
            # Registrar no log
            self.logger.info(f"Backup criado: {backup_filename}")
            
            # Limpar backups antigos
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Erro ao criar backup: {str(e)}")
            return None
    
    def _backup_sqlite(self, backup_path: str):
        """
        Cria backup usando a API de backup do SQLite (mais seguro)
        """
        # Conectar ao banco de dados original
        source_conn = sqlite3.connect(self.db_path)
        source_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")  # Forçar checkpoint
        
        # Conectar ao banco de backup
        dest_conn = sqlite3.connect(backup_path)
        
        # Realizar backup online
        with source_conn:
            source_conn.backup(dest_conn, pages=1000)  # Backup em lotes de 1000 páginas
        
        # Fechar conexões
        source_conn.close()
        dest_conn.close()
    
    def _cleanup_old_backups(self, days_to_keep: int = 30):
        """
        Remove backups mais antigos que days_to_keep dias
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for filename in os.listdir(self.backup_dir):
            if not filename.startswith("backup_") or not filename.endswith(".db"):
                continue
            
            file_path = os.path.join(self.backup_dir, filename)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_time < cutoff_date:
                try:
                    os.remove(file_path)
                    self.logger.info(f"Backup antigo removido: {filename}")
                except Exception as e:
                    self.logger.error(f"Erro ao remover backup {filename}: {str(e)}")
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restaura um backup para o banco de dados principal
        
        Args:
            backup_path: Caminho do arquivo de backup
            
        Returns:
            True se a restauração foi bem-sucedida, False caso contrário
        """
        try:
            # Verificar se o backup existe
            if not os.path.exists(backup_path):
                self.logger.error(f"Arquivo de backup não encontrado: {backup_path}")
                return False
            
            # Fazer backup de segurança antes de restaurar
            safety_backup = self.create_backup("before_restore")
            
            # Restaurar o backup
            source_conn = sqlite3.connect(backup_path)
            dest_conn = sqlite3.connect(self.db_path)
            
            with source_conn:
                source_conn.backup(dest_conn)
            
            source_conn.close()
            dest_conn.close()
            
            self.logger.info(f"Backup restaurado: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao restaurar backup: {str(e)}")
            return False
    
    def list_backups(self) -> list:
        """
        Lista todos os backups disponíveis
        
        Returns:
            Lista de dicionários com informações dos backups
        """
        backups = []
        
        for filename in sorted(os.listdir(self.backup_dir), reverse=True):
            if not filename.startswith("backup_") or not filename.endswith(".db"):
                continue
            
            file_path = os.path.join(self.backup_dir, filename)
            stat = os.stat(file_path)
            
            backups.append({
                "filename": filename,
                "path": file_path,
                "size": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime)
            })
        
        return backups
    
    def start_auto_backup(self, interval_hours: int = 24, callback: Optional[Callable] = None):
        """
        Inicia backups automáticos em uma thread separada
        
        Args:
            interval_hours: Intervalo entre backups em horas
            callback: Função a ser chamada após cada backup
        """
        if self.running:
            self.logger.warning("Backup automático já está em execução")
            return
        
        self.running = True
        
        def backup_job():
            self.logger.info(f"Iniciando backup automático (intervalo: {interval_hours}h)")
            result = self.create_backup("auto")
            if callback and result:
                callback(result)
        
        # Agendar o backup
        schedule.every(interval_hours).hours.do(backup_job)
        
        # Executar um backup imediatamente
        backup_job()
        
        # Iniciar thread para executar o scheduler
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Verificar a cada minuto
        
        self.backup_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.backup_thread.start()
        
        self.logger.info(f"Backup automático iniciado. Intervalo: {interval_hours} horas")
    
    def stop_auto_backup(self):
        """Para os backups automáticos"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        self.logger.info("Backup automático parado")


class BackupScheduler:
    """
    Interface para agendamento de backups via Streamlit
    """
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.schedule_file = os.path.join(backup_manager.backup_dir, "schedule.txt")
    
    def save_schedule(self, interval_hours: int, enabled: bool):
        """
        Salva a configuração de agendamento
        """
        with open(self.schedule_file, 'w') as f:
            f.write(f"enabled={enabled}\n")
            f.write(f"interval={interval_hours}\n")
            f.write(f"updated={datetime.now().isoformat()}\n")
    
    def load_schedule(self) -> dict:
        """
        Carrega a configuração de agendamento
        """
        default = {"enabled": False, "interval": 24}
        
        if not os.path.exists(self.schedule_file):
            return default
        
        try:
            config = {}
            with open(self.schedule_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == 'enabled':
                            config[key] = value.lower() == 'true'
                        elif key == 'interval':
                            config[key] = int(value)
                        else:
                            config[key] = value
            return config
        except:
            return default