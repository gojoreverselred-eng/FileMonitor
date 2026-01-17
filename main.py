from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform
import os
import json
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
import threading

class ConfigManager:
    def __init__(self):
        if platform == 'android':
            from android.storage import app_storage_path
            self.config_dir = app_storage_path()
        else:
            self.config_dir = os.path.expanduser("~")
        
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.webhook_url = data.get('webhook_url', '')
                self.watch_dir = data.get('watch_dir', '')
                self.message_template = data.get('message_template', 'File: {filename}\nDir: {dir}\nDate: {dirdate}')
        else:
            self.webhook_url = ''
            self.watch_dir = ''
            self.message_template = 'File: {filename}\nDir: {dir}\nDate: {dirdate}'
    
    def save_config(self):
        data = {
            'webhook_url': self.webhook_url,
            'watch_dir': self.watch_dir,
            'message_template': self.message_template
        }
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)

class FileMonitorHandler(FileSystemEventHandler):
    def __init__(self, webhook_url, message_template, log_callback):
        self.webhook_url = webhook_url
        self.message_template = message_template
        self.log_callback = log_callback
    
    def on_created(self, event):
        if not event.is_directory:
            self.send_webhook(event.src_path)
    
    def send_webhook(self, filepath):
        import hashlib
        
        filename = os.path.basename(filepath)
        directory = os.path.dirname(filepath)
        dirdate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            filesize_bytes = os.path.getsize(filepath)
            if filesize_bytes < 1024:
                filesize = f"{filesize_bytes} B"
            elif filesize_bytes < 1024 * 1024:
                filesize = f"{filesize_bytes / 1024:.2f} KB"
            elif filesize_bytes < 1024 * 1024 * 1024:
                filesize = f"{filesize_bytes / (1024 * 1024):.2f} MB"
            else:
                filesize = f"{filesize_bytes / (1024 * 1024 * 1024):.2f} GB"
        except:
            filesize = "Unknown"
        
        filetype = os.path.splitext(filename)[1]
        filepath_full = os.path.abspath(filepath)
        time_only = datetime.now().strftime("%H:%M:%S")
        date_only = datetime.now().strftime("%Y-%m-%d")
        timestamp = str(int(datetime.now().timestamp()))
        foldername = os.path.basename(directory)
        
        try:
            filecount = len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
        except:
            filecount = "Unknown"
        
        try:
            with open(filepath, 'rb') as f:
                filehash = hashlib.md5(f.read()).hexdigest()
        except:
            filehash = "Unknown"
        
        rtnfile = directory
        
        message = self.message_template.format(
            filename=filename,
            dir=directory,
            dirdate=dirdate,
            filesize=filesize,
            filetype=filetype,
            filepath=filepath_full,
            time=time_only,
            date=date_only,
            timestamp=timestamp,
            foldername=foldername,
            filecount=filecount,
            filehash=filehash,
            alert="@everyone",
            rtnfile=rtnfile
        )
        
        payload = {"content": message}
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 204:
                self.log_callback(f"✓ Sent: {filename}")
            else:
                self.log_callback(f"✗ Failed: {response.status_code}")
        except Exception as e:
            self.log_callback(f"✗ Error: {str(e)[:50]}")

class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = ConfigManager()
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text='File Monitor Setup', font_size=24, size_hint_y=0.1))
        
        layout.add_widget(Label(text='Discord Webhook URL:', size_hint_y=0.05))
        self.webhook_input = TextInput(text=self.config.webhook_url, multiline=False, size_hint_y=0.08)
        layout.add_widget(self.webhook_input)
        
        layout.add_widget(Label(text='Folder Path:', size_hint_y=0.05))
        self.path_input = TextInput(text=self.config.watch_dir, multiline=False, size_hint_y=0.08)
        layout.add_widget(self.path_input)
        
        layout.add_widget(Label(text='Message Template:', size_hint_y=0.05))
        layout.add_widget(Label(text='Variables: {filename} {dir} {dirdate} {filesize} {filetype} {filepath} {time} {date} {timestamp} {foldername} {filecount} {filehash} {alert} {rtnfile}', size_hint_y=0.06, font_size=10))
        self.template_input = TextInput(text=self.config.message_template, multiline=True, size_hint_y=0.15)
        layout.add_widget(self.template_input)
        
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
        
        save_btn = Button(text='Save')
        save_btn.bind(on_press=self.save_config)
        btn_layout.add_widget(save_btn)
        
        test_btn = Button(text='Test')
        test_btn.bind(on_press=self.test_webhook)
        btn_layout.add_widget(test_btn)
        
        layout.add_widget(btn_layout)
        
        start_btn = Button(text='Start Monitoring', size_hint_y=0.1)
        start_btn.bind(on_press=self.go_to_monitor)
        layout.add_widget(start_btn)
        
        self.status_label = Label(text='', size_hint_y=0.1)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def save_config(self, instance):
        self.config.webhook_url = self.webhook_input.text
        self.config.watch_dir = self.path_input.text
        self.config.message_template = self.template_input.text
        self.config.save_config()
        self.status_label.text = '✓ Saved!'
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', ''), 3)
    
    def test_webhook(self, instance):
        if not self.webhook_input.text:
            self.status_label.text = '✗ Enter webhook first'
            return
        
        test_msg = self.template_input.text.format(
            filename="test.txt",
            dir="/test",
            dirdate=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            filesize="1.5 KB",
            filetype=".txt",
            filepath="/test/test.txt",
            time=datetime.now().strftime("%H:%M:%S"),
            date=datetime.now().strftime("%Y-%m-%d"),
            timestamp=str(int(datetime.now().timestamp())),
            foldername="test",
            filecount="5",
            filehash="d41d8cd98f00b204e9800998ecf8427e",
            alert="@everyone",
            rtnfile="/test"
        )
        
        try:
            response = requests.post(self.webhook_input.text, json={"content": test_msg}, timeout=10)
            if response.status_code == 204:
                self.status_label.text = '✓ Test sent!'
            else:
                self.status_label.text = f'✗ Failed: {response.status_code}'
        except Exception as e:
            self.status_label.text = f'✗ Error'
        
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', ''), 3)
    
    def go_to_monitor(self, instance):
        self.save_config(instance)
        self.manager.current = 'monitor'
        self.manager.get_screen('monitor').start_monitoring()

class MonitorScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observer = None
        self.is_monitoring = False
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(text='File Monitor', font_size=24, size_hint_y=0.08))
        
        self.status_label = Label(text='Status: Stopped', size_hint_y=0.06)
        layout.add_widget(self.status_label)
        
        self.info_label = Label(text='', size_hint_y=0.1, font_size=12)
        layout.add_widget(self.info_label)
        
        scroll = ScrollView(size_hint_y=0.5)
        self.log_label = Label(text='Waiting for files...', size_hint_y=None, font_size=12)
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll.add_widget(self.log_label)
        layout.add_widget(scroll)
        
        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=10)
        
        stop_btn = Button(text='Stop')
        stop_btn.bind(on_press=self.stop_monitoring)
        btn_layout.add_widget(stop_btn)
        
        back_btn = Button(text='Back to Setup')
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'setup'))
        btn_layout.add_widget(back_btn)
        
        layout.add_widget(btn_layout)
        
        self.add_widget(layout)
        self.logs = []
    
    def add_log(self, message):
        self.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        if len(self.logs) > 50:
            self.logs.pop(0)
        Clock.schedule_once(lambda dt: setattr(self.log_label, 'text', '\n'.join(self.logs)))
    
    def start_monitoring(self):
        config = ConfigManager()
        
        if not config.webhook_url or not config.watch_dir:
            self.add_log('✗ Config incomplete!')
            return
        
        if not os.path.exists(config.watch_dir):
            self.add_log(f'✗ Directory not found!')
            return
        
        self.status_label.text = 'Status: Running'
        self.info_label.text = f'Watching: {config.watch_dir}'
        
        event_handler = FileMonitorHandler(config.webhook_url, config.message_template, self.add_log)
        self.observer = Observer()
        self.observer.schedule(event_handler, config.watch_dir, recursive=True)
        
        def run_observer():
            self.observer.start()
            self.is_monitoring = True
            self.add_log('✓ Monitoring started!')
        
        threading.Thread(target=run_observer, daemon=True).start()
    
    def stop_monitoring(self, instance):
        if self.observer and self.is_monitoring:
            self.observer.stop()
            self.observer.join()
            self.is_monitoring = False
            self.status_label.text = 'Status: Stopped'
            self.add_log('✓ Monitoring stopped')

class FileMonitorApp(App):
    def build(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.INTERNET
            ])
        
        sm = ScreenManager()
        sm.add_widget(SetupScreen(name='setup'))
        sm.add_widget(MonitorScreen(name='monitor'))
        return sm

if __name__ == '__main__':
    FileMonitorApp().run()
