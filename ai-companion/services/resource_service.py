import psutil
import time
import os
import subprocess
import json

class ResourceService:
    def __init__(self, config):
        self.config = config
        self.max_cpu = config['system'].get('max_cpu_percent', 85)
        self.max_ram = config['system'].get('max_ram_percent', 90)
        self.max_vram = config['hardware'].get('gpu_vram_gb', 4)
        
        # Priority Queues
        self.background_tasks_paused = False
        self.start_time = time.time()

    def get_system_stats(self):
        """Returns a snapshot of current bare metal resource usage."""
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "uptime": int(time.time() - self.start_time),
            "vram_used_gb": 0,
            "processes": {}
        }

        # Try to get VRAM usage via nvidia-smi (Bare metal Linux standard)
        try:
            vram_info = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"],
                encoding='utf-8'
            )
            stats["vram_used_gb"] = round(int(vram_info.strip()) / 1024, 2)
        except Exception:
            stats["vram_used_gb"] = "N/A"

        # Monitor specific heavy hitters
        heavy_hitters = ["ollama", "postgres", "redis", "node", "python3"]
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                name = proc.info['name'].lower()
                if any(hh in name for hh in heavy_hitters):
                    if name not in stats["processes"]:
                        stats["processes"][name] = {"cpu": 0, "mem": 0, "count": 0}
                    stats["processes"][name]["cpu"] += proc.info['cpu_percent']
                    stats["processes"][name]["mem"] += proc.info['memory_percent']
                    stats["processes"][name]["count"] += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return stats

    def should_throttle(self):
        """Returns True if the system is approaching 'lag like a mf' territory."""
        stats = self.get_system_stats()
        
        # Check CPU/RAM
        if stats["cpu_percent"] > self.max_cpu: return True
        if stats["ram_percent"] > self.max_ram: return True
        
        # Check VRAM (If 4GB, we want to stay under 3.5GB to avoid swap/stutter)
        if isinstance(stats["vram_used_gb"], (int, float)):
            if stats["vram_used_gb"] > (self.max_vram * 0.9):
                return True
                
        return False

    def get_priority_multiplier(self, current_state):
        """
        Adjusts the engine loop interval based on system load and current state.
        Returns a multiplier for the loop sleep time.
        """
        if self.should_throttle():
            return 3.0 # Slow down significantly (15s instead of 5s)
        
        # If the child is actively engaged, we want high responsiveness
        if current_state in ["ENGAGED", "DECIDING", "SPEAKING"]:
            return 0.5 # Speed up (2.5s instead of 5s)
            
        return 1.0 # Standard (5s)

    def can_run_background_task(self):
        """Firecrawl/Search/Research should only run if resources are plenty."""
        stats = self.get_system_stats()
        # Firecrawl is heavy. Only run if CPU < 50% and RAM < 70%
        return stats["cpu_percent"] < 50 and stats["ram_percent"] < 70

    def get_quality_mode(self):
        """Maps system load to research quality levels (high, medium, low)."""
        stats = self.get_system_stats()
        
        if stats["cpu_percent"] < 40 and stats["ram_percent"] < 60:
            return "high"
        elif stats["cpu_percent"] < 70 and stats["ram_percent"] < 85:
            return "medium"
        else:
            return "low"
