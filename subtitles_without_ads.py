#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import queue
import re
import shutil
import tempfile
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

APP_VERSION = '1.1.2'

DEFAULT_KEYWORDS = [
    'www.titlovi.com',
    'titlovi.com',
    'opensubtitles',
    'opensubtitles.org',
    'opensubtitles.com',
    'podnapisi.net',
    'subscene.com',
    'addic7ed.com',
    'yts.mx',
    'yify',
    'bsplayer-subtitles.com',
    'tvsubtitles.net',
    'prijevodi-online.org',
    'subtitlovi.com',
    'divx-titlovi.com',
    'subdl.com',
    'subsource.net',
    'subtitleseeker',
    'opensubtitles.net',
    'http://',
    'https://',
    'www.',
    'facebook.com',
    'instagram.com',
    'twitter.com',
    'x.com/',
    't.me/',
    'telegram.me',
    'discord.gg',
    'patreon.com',
    'paypal.me',
    'ko-fi.com',
    'preveo',
    'prevela',
    'prijevod',
    'prevod',
    'obrada',
    'prijevod i obrada',
    'prevod i obrada',
    'preveo i obradio',
    'sinkronizirao',
    'sinkronizirala',
    'sinkronizacija',
    'translated by',
    'translation by',
    'translated and synced by',
    'subtitle by',
    'subtitles by',
    'subtitles downloaded from',
    'download subtitles from',
    'download more subtitles',
    'subtitulado por',
    'traducido por',
    'legendas por',
    'sync by',
    'synced by',
    'resync by',
    'resynced by',
    'sync and corrections by',
    'sync & corrections by',
    'corrected and synced by',
    'resync and corrections by',
    'corrected by',
    'edited by',
    'adapted by',
    'timing by',
    'uploaded by',
    'encoded by',
    'ripped by',
    'captioned by',
    'downloaded from',
    'visit us at',
    'like us on facebook',
    'follow us on',
    'posjetite nas',
    'pratite nas',
    'zapratite nas',
    'podržite nas',
    'podrzite nas',
    'hvala što koristite',
    'hvala sto koristite'
]

class SRTCleanerApp:
    def __init__(self, root):
        self.root = root
        self._main_thread = threading.current_thread()
        self._ui_queue = queue.Queue()
        self.language = 'hr'  # Default language
        self.root.title(f"Subtitles Without Ads - Verzija {APP_VERSION}")
        self.root.geometry("950x800")
        self.root.resizable(True, True)
        
        # Varijable
        self.selected_folder = None
        self.srt_files = []
        self.is_processing = False
        self.create_backups = True  # Default: create backups
        self.stats = {
            'total': 0,
            'cleaned': 0,
            'already_clean': 0,
            'blocks_removed': 0,
            'errors': 0
        }
        
        # Detailed results
        self.cleaned_files = []
        self.already_clean_files = []
        self.error_files = []
        self.removed_blocks_details = {}  # filename: [removed blocks]
        
        # Ključne riječi za filtriranje
        self.keywords = DEFAULT_KEYWORDS.copy()
        
        # Translations
        self.translations = {
            'hr': {
                'title': f'Subtitles Without Ads - Verzija {APP_VERSION}',
                'header': 'Subtitles Without Ads',
                'subtitle': 'Čišćenje SRT titlova od reklama, potpisa i promotivnog teksta',
                'folder_selection': 'Odabir foldera',
                'no_folder': 'Nije odabran folder',
                'browse': 'Odaberi folder',
                'keywords': 'Ključne riječi',
                'keywords_info': 'Blokovi titlova koji sadrže ove riječi bit će uklonjeni:',
                'save_changes': 'Spremi promjene',
                'reset': 'Vrati zadano',
                'statistics': 'Statistika',
                'total_files': 'Ukupno datoteka',
                'cleaned': 'Očišćeno',
                'already_clean': 'Već čisto',
                'blocks_removed': 'Uklonjeno blokova',
                'errors': 'Greške',
                'log': 'Dnevnik obrade',
                'start': 'Pokreni čišćenje',
                'clear_log': 'Očisti dnevnik',
                'status_ready': 'Spremno. Odaberi folder za početak.',
                'welcome': 'Subtitles Without Ads je spreman.',
                'select_folder': 'Odaberite folder s .srt datotekama za početak.',
                'buy_coffee': 'Plati kavu',
                'language': 'English',
                'backup_option': 'Kreiraj backup datoteke',
                'view_cleaned': 'Prikaži očišćene',
                'view_clean': 'Prikaži čiste',
                'view_removed': 'Prikaži uklonjeno',
                'about': 'O programu'
            },
            'en': {
                'title': f'Subtitles Without Ads - Version {APP_VERSION}',
                'header': 'Subtitles Without Ads',
                'subtitle': 'Clean SRT subtitles from ads, credits and promotional text',
                'folder_selection': 'Folder selection',
                'no_folder': 'No folder selected',
                'browse': 'Browse folder',
                'keywords': 'Filter keywords',
                'keywords_info': 'Subtitle blocks containing these words will be removed:',
                'save_changes': 'Save changes',
                'reset': 'Reset default',
                'statistics': 'Statistics',
                'total_files': 'Total Files',
                'cleaned': 'Cleaned',
                'already_clean': 'Already Clean',
                'blocks_removed': 'Blocks Removed',
                'errors': 'Errors',
                'log': 'Processing log',
                'start': 'Start cleaning',
                'clear_log': 'Clear log',
                'status_ready': 'Ready. Select folder to begin.',
                'welcome': 'Subtitles Without Ads is ready.',
                'select_folder': 'Select a folder with .srt files to begin.',
                'buy_coffee': 'Buy me a coffee',
                'language': 'Hrvatski',
                'backup_option': 'Create backup files',
                'view_cleaned': 'View cleaned',
                'view_clean': 'View clean',
                'view_removed': 'View removed',
                'about': 'About'
            }
        }
        
        self._build_ui()
        self.root.after(50, self.process_ui_queue)
        
    def is_ui_thread(self):
        return threading.current_thread() is self._main_thread
    
    def run_on_ui_thread(self, callback, *args, **kwargs):
        if self.is_ui_thread():
            callback(*args, **kwargs)
        else:
            self._ui_queue.put((callback, args, kwargs))
    
    def process_ui_queue(self):
        try:
            while True:
                callback, args, kwargs = self._ui_queue.get_nowait()
                try:
                    callback(*args, **kwargs)
                except tk.TclError:
                    pass
        except queue.Empty:
            pass
        
        try:
            self.root.after(50, self.process_ui_queue)
        except tk.TclError:
            pass
    
    def t(self, key):
        """Get translation for current language"""
        return self.translations[self.language].get(key, key)
    
    def toggle_language(self):
        """Toggle between Croatian and English"""
        self.language = 'en' if self.language == 'hr' else 'hr'
        self.refresh_ui()
    
    def show_about(self):
        """Show About dialog"""
        about_window = tk.Toplevel(self.root)
        title = "O Programu" if self.language == 'hr' else "About"
        about_window.title(title)
        about_window.geometry("560x520")
        about_window.minsize(520, 460)
        about_window.configure(bg=self.colors['background'])
        about_window.resizable(True, True)
        
        if self.language == 'hr':
            info_text = f"""
Verzija: {APP_VERSION}

Program za automatsko čišćenje SRT titlova od reklama, 
prevoditelja i promotivnog teksta.

Značajke:
• Automatsko skeniranje foldera
• Prilagodljive ključne riječi
• Backup datoteke (.bak)
• Višejezična podrška (HR/EN)
• Detaljna statistika i izvještaji
• Pregled uklonjenih blokova

Razvio: Danijel
Godina: 2025

Licenca: Besplatno za osobnu upotrebu

Ako vam se program sviđa, možete podržati 
razvoj kupovinom kave.
            """
        else:
            info_text = f"""
Version: {APP_VERSION}

Program for automatic cleaning of SRT subtitles from ads,
translators and promotional text.

Features:
• Automatic folder scanning
• Customizable keywords
• Backup files (.bak)
• Multilingual support (HR/EN)
• Detailed statistics and reports
• View removed blocks

Developer: Danijel
Year: 2025

License: Free for personal use

If you like this program, you can support 
development by buying me a coffee.
            """
        
        container = self.make_panel(about_window, padx=22, pady=22)
        container.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)
        
        title_label = tk.Label(
            container,
            text=self.t('header'),
            font=('Segoe UI', 18, 'bold'),
            bg=self.colors['surface'],
            fg=self.colors['text'],
            anchor=tk.W
        )
        title_label.grid(row=0, column=0, sticky='ew')
        
        text_widget = scrolledtext.ScrolledText(
            container,
            font=self.fonts['body'],
            wrap=tk.WORD,
            bg='#fbfdff',
            fg=self.colors['text'],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12
        )
        text_widget.grid(row=1, column=0, sticky='nsew', pady=(14, 14))
        text_widget.insert(tk.END, info_text.strip())
        text_widget.config(state=tk.DISABLED)
        
        btn_frame = tk.Frame(container, bg=self.colors['surface'])
        btn_frame.grid(row=2, column=0, sticky='ew')
        
        coffee_text = "Plati kavu" if self.language == 'hr' else "Buy me a coffee"
        btn_coffee = self.make_button(
            btn_frame,
            coffee_text,
            lambda: webbrowser.open('https://www.paypal.com/paypalme/danijel0304'),
            'coffee',
            14,
            8
        )
        btn_coffee.pack(side=tk.LEFT, padx=(30, 10))
        
        close_text = "Zatvori" if self.language == 'hr' else "Close"
        btn_close = self.make_button(btn_frame, close_text, about_window.destroy, 'secondary', 14, 8)
        btn_close.pack(side=tk.RIGHT)
    
    def refresh_ui(self):
        """Refresh all UI text elements"""
        self.root.title(self.t('title'))
        self.header_title.config(text=self.t('header'))
        self.header_subtitle.config(text=self.t('subtitle'))
        self.folder_frame.config(text=self.t('folder_selection'))
        if not self.selected_folder:
            self.folder_label.config(text=self.t('no_folder'))
        self.btn_browse.config(text=self.t('browse'))
        self.keywords_frame.config(text=self.t('keywords'))
        self.keywords_info.config(text=self.t('keywords_info'))
        self.btn_save_keywords.config(text=self.t('save_changes'))
        self.btn_reset_keywords.config(text=self.t('reset'))
        self.stats_frame.config(text=self.t('statistics'))
        self.log_frame.config(text=self.t('log'))
        self.btn_start.config(text=self.t('start'))
        self.btn_clear.config(text=self.t('clear_log'))
        self.btn_coffee.config(text=self.t('buy_coffee'))
        self.btn_language.config(text=self.t('language'))
        self.btn_about.config(text=self.t('about'))
        self.backup_check.config(text=self.t('backup_option'))
        self.btn_view_cleaned.config(text=self.t('view_cleaned'))
        self.btn_view_clean.config(text=self.t('view_clean'))
        self.btn_view_removed.config(text=self.t('view_removed'))
        
        # Update stat labels
        stat_keys = ['total_files', 'cleaned', 'already_clean', 'blocks_removed', 'errors']
        for i, key in enumerate(['total', 'cleaned', 'already_clean', 'blocks_removed', 'errors']):
            self.stat_text_labels[key].config(text=self.t(stat_keys[i]))
        
        if not self.is_processing:
            self.status_bar.config(text=self.t('status_ready'))
    
    def configure_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'App.TCheckbutton',
            background=self.colors['surface'],
            foreground=self.colors['text'],
            font=self.fonts['body']
        )
        style.map('App.TCheckbutton', background=[('active', self.colors['surface'])])
        style.configure(
            'App.Horizontal.TProgressbar',
            troughcolor=self.colors['surface_alt'],
            background=self.colors['primary'],
            bordercolor=self.colors['border'],
            lightcolor=self.colors['primary'],
            darkcolor=self.colors['primary']
        )
    
    def make_button(self, parent, text, command, variant='secondary', padx=14, pady=8):
        variants = {
            'primary': (self.colors['primary'], 'white', self.colors['primary_hover'], self.colors['primary_hover']),
            'success': (self.colors['success'], 'white', self.colors['success_hover'], self.colors['success_hover']),
            'secondary': (self.colors['surface'], self.colors['text'], self.colors['surface_alt'], self.colors['border']),
            'muted': (self.colors['muted_button'], self.colors['text'], self.colors['border'], self.colors['border']),
            'coffee': (self.colors['coffee'], 'white', self.colors['coffee_hover'], self.colors['coffee_hover'])
        }
        bg, fg, active_bg, border = variants[variant]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            disabledforeground=self.colors['disabled'],
            font=self.fonts['button'],
            padx=padx,
            pady=pady,
            bd=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=border,
            cursor="hand2"
        )
    
    def make_panel(self, parent, padx=18, pady=18):
        return tk.Frame(
            parent,
            bg=self.colors['surface'],
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=self.colors['border']
        )
    
    def make_section_label(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            font=self.fonts['section'],
            anchor=tk.W
        )
    
    def bind_click(self, widget, callback):
        widget.config(cursor="hand2")
        widget.bind("<Button-1>", lambda _event, cb=callback: cb())
    
    def _build_ui(self):
        self.root.geometry("1120x760")
        self.root.minsize(980, 680)
        
        self.colors = {
            'background': '#f5f7fb',
            'surface': '#ffffff',
            'surface_alt': '#eef3f8',
            'border': '#d7dee8',
            'text': '#17202a',
            'muted': '#667085',
            'disabled': '#98a2b3',
            'primary': '#2563eb',
            'primary_hover': '#1d4ed8',
            'success': '#0f9f6e',
            'success_hover': '#0b7f59',
            'warning': '#b7791f',
            'danger': '#dc2626',
            'dark': '#17202a',
            'light': '#eef3f8',
            'coffee': '#8b5e34',
            'coffee_hover': '#6f4727',
            'muted_button': '#f8fafc',
            'log_bg': '#111827',
            'log_fg': '#e5e7eb'
        }
        self.fonts = {
            'title': ('Segoe UI', 22, 'bold'),
            'subtitle': ('Segoe UI', 10),
            'section': ('Segoe UI', 11, 'bold'),
            'body': ('Segoe UI', 10),
            'button': ('Segoe UI', 10, 'bold'),
            'stat_value': ('Segoe UI', 23, 'bold'),
            'stat_label': ('Segoe UI', 9),
            'mono': ('Consolas', 10)
        }
        
        self.configure_theme()
        self.root.configure(bg=self.colors['background'])
        
        # Header
        header_frame = tk.Frame(
            self.root,
            bg=self.colors['surface'],
            padx=22,
            pady=16,
            highlightthickness=1,
            highlightbackground=self.colors['border']
        )
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.columnconfigure(0, weight=1)
        header_frame.columnconfigure(1, weight=0)
        
        title_frame = tk.Frame(header_frame, bg=self.colors['surface'])
        title_frame.grid(row=0, column=0, sticky='ew')
        
        self.header_title = tk.Label(
            title_frame,
            text=self.t('header'),
            font=self.fonts['title'],
            bg=self.colors['surface'],
            fg=self.colors['text'],
            anchor=tk.W
        )
        self.header_title.pack(anchor=tk.W)
        
        self.header_subtitle = tk.Label(
            title_frame,
            text=self.t('subtitle'),
            font=self.fonts['subtitle'],
            bg=self.colors['surface'],
            fg=self.colors['muted'],
            anchor=tk.W
        )
        self.header_subtitle.pack(anchor=tk.W, pady=(2, 0))
        
        header_buttons = tk.Frame(header_frame, bg=self.colors['surface'])
        header_buttons.grid(row=0, column=1, sticky='e')
        
        self.btn_language = self.make_button(header_buttons, self.t('language'), self.toggle_language, 'secondary', 12, 7)
        self.btn_language.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_about = self.make_button(header_buttons, self.t('about'), self.show_about, 'secondary', 12, 7)
        self.btn_about.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_coffee = self.make_button(
            header_buttons,
            self.t('buy_coffee'),
            lambda: webbrowser.open('https://www.paypal.com/paypalme/danijel0304'),
            'coffee',
            12,
            7
        )
        self.btn_coffee.pack(side=tk.LEFT)
        
        # Main content
        main_frame = tk.Frame(self.root, bg=self.colors['background'], padx=18, pady=18)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=0, minsize=380)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        left_panel = self.make_panel(main_frame)
        left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 14))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(5, weight=1)
        
        self.folder_frame = self.make_section_label(left_panel, self.t('folder_selection'))
        self.folder_frame.grid(row=0, column=0, sticky='ew')
        
        folder_row = tk.Frame(left_panel, bg=self.colors['surface'])
        folder_row.grid(row=1, column=0, sticky='ew', pady=(10, 12))
        folder_row.columnconfigure(0, weight=1)
        
        self.folder_label = tk.Label(
            folder_row,
            text=self.t('no_folder'),
            font=self.fonts['body'],
            fg=self.colors['muted'],
            bg=self.colors['surface_alt'],
            anchor=tk.W,
            justify=tk.LEFT,
            padx=12,
            pady=10,
            highlightthickness=1,
            highlightbackground=self.colors['border']
        )
        self.folder_label.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        
        self.btn_browse = self.make_button(folder_row, self.t('browse'), self.browse_folder, 'primary', 14, 9)
        self.btn_browse.grid(row=0, column=1, sticky='e')
        
        self.backup_var = tk.BooleanVar(value=True)
        self.backup_check = ttk.Checkbutton(
            left_panel,
            text=self.t('backup_option'),
            variable=self.backup_var,
            command=self.toggle_backup,
            style='App.TCheckbutton'
        )
        self.backup_check.grid(row=2, column=0, sticky='w', pady=(0, 20))
        
        self.keywords_frame = self.make_section_label(left_panel, self.t('keywords'))
        self.keywords_frame.grid(row=3, column=0, sticky='ew')
        
        self.keywords_info = tk.Label(
            left_panel,
            text=self.t('keywords_info'),
            font=self.fonts['body'],
            bg=self.colors['surface'],
            fg=self.colors['muted'],
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.keywords_info.grid(row=4, column=0, sticky='ew', pady=(6, 8))
        
        self.keywords_text = scrolledtext.ScrolledText(
            left_panel,
            height=14,
            font=self.fonts['mono'],
            wrap=tk.WORD,
            bg='#fbfdff',
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        self.keywords_text.grid(row=5, column=0, sticky='nsew')
        self.keywords_text.insert('1.0', ', '.join(self.keywords))
        
        keywords_btn_frame = tk.Frame(left_panel, bg=self.colors['surface'])
        keywords_btn_frame.grid(row=6, column=0, sticky='ew', pady=(12, 0))
        
        self.btn_save_keywords = self.make_button(keywords_btn_frame, self.t('save_changes'), self.update_keywords, 'primary', 12, 8)
        self.btn_save_keywords.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_reset_keywords = self.make_button(keywords_btn_frame, self.t('reset'), self.reset_keywords, 'secondary', 12, 8)
        self.btn_reset_keywords.pack(side=tk.LEFT)
        
        right_panel = tk.Frame(main_frame, bg=self.colors['background'])
        right_panel.grid(row=0, column=1, sticky='nsew')
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        stats_panel = self.make_panel(right_panel)
        stats_panel.grid(row=0, column=0, sticky='ew')
        stats_panel.columnconfigure(0, weight=1)
        
        self.stats_frame = self.make_section_label(stats_panel, self.t('statistics'))
        self.stats_frame.grid(row=0, column=0, sticky='ew')
        
        stats_grid = tk.Frame(stats_panel, bg=self.colors['surface'])
        stats_grid.grid(row=1, column=0, sticky='ew', pady=(12, 12))
        
        self.stat_labels = {}
        self.stat_text_labels = {}
        stat_items = [
            ('total', 'total_files', self.colors['primary'], None),
            ('cleaned', 'cleaned', self.colors['success'], self.show_cleaned_files),
            ('already_clean', 'already_clean', self.colors['warning'], self.show_clean_files),
            ('blocks_removed', 'blocks_removed', self.colors['danger'], self.show_removed_blocks),
            ('errors', 'errors', self.colors['muted'], None)
        ]
        
        for i, (key, label_key, color, callback) in enumerate(stat_items):
            stats_grid.columnconfigure(i, weight=1, uniform='stats')
            stat_box = tk.Frame(
                stats_grid,
                bg=self.colors['surface_alt'],
                width=126,
                height=92,
                highlightthickness=1,
                highlightbackground=self.colors['border']
            )
            stat_box.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 7, 0))
            stat_box.grid_propagate(False)
            stat_box.columnconfigure(0, weight=1)
            
            value_lbl = tk.Label(
                stat_box,
                text="0",
                font=self.fonts['stat_value'],
                bg=self.colors['surface_alt'],
                fg=color
            )
            value_lbl.grid(row=0, column=0, sticky='ew', pady=(12, 0))
            
            text_lbl = tk.Label(
                stat_box,
                text=self.t(label_key),
                font=self.fonts['stat_label'],
                bg=self.colors['surface_alt'],
                fg=self.colors['muted']
            )
            text_lbl.grid(row=1, column=0, sticky='ew')
            
            if callback:
                self.bind_click(stat_box, callback)
                self.bind_click(value_lbl, callback)
                self.bind_click(text_lbl, callback)
            
            self.stat_labels[key] = value_lbl
            self.stat_text_labels[key] = text_lbl
        
        detail_buttons = tk.Frame(stats_panel, bg=self.colors['surface'])
        detail_buttons.grid(row=2, column=0, sticky='ew')
        self.btn_view_cleaned = self.make_button(detail_buttons, self.t('view_cleaned'), self.show_cleaned_files, 'secondary', 10, 7)
        self.btn_view_cleaned.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_view_clean = self.make_button(detail_buttons, self.t('view_clean'), self.show_clean_files, 'secondary', 10, 7)
        self.btn_view_clean.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_view_removed = self.make_button(detail_buttons, self.t('view_removed'), self.show_removed_blocks, 'secondary', 10, 7)
        self.btn_view_removed.pack(side=tk.LEFT)
        
        log_panel = self.make_panel(right_panel)
        log_panel.grid(row=1, column=0, sticky='nsew', pady=(14, 0))
        log_panel.columnconfigure(0, weight=1)
        log_panel.rowconfigure(1, weight=1)
        
        self.log_frame = self.make_section_label(log_panel, self.t('log'))
        self.log_frame.grid(row=0, column=0, sticky='ew')
        
        self.log_text = scrolledtext.ScrolledText(
            log_panel,
            height=14,
            font=('Consolas', 9),
            wrap=tk.WORD,
            bg=self.colors['log_bg'],
            fg=self.colors['log_fg'],
            insertbackground=self.colors['log_fg'],
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12
        )
        self.log_text.grid(row=1, column=0, sticky='nsew', pady=(10, 0))
        self.log_text.tag_config('success', foreground='#34d399')
        self.log_text.tag_config('warning', foreground='#fbbf24')
        self.log_text.tag_config('error', foreground='#f87171')
        self.log_text.tag_config('info', foreground='#93c5fd')
        
        action_container = tk.Frame(
            self.root,
            bg=self.colors['surface'],
            padx=18,
            pady=12,
            highlightthickness=1,
            highlightbackground=self.colors['border']
        )
        action_container.pack(side=tk.BOTTOM, fill=tk.X, before=main_frame)
        action_container.columnconfigure(0, weight=0)
        action_container.columnconfigure(1, weight=1)
        
        action_buttons = tk.Frame(action_container, bg=self.colors['surface'])
        action_buttons.grid(row=0, column=0, sticky='w')
        
        self.btn_start = self.make_button(action_buttons, self.t('start'), self.start_cleaning, 'success', 22, 10)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 10))
        
        self.btn_clear = self.make_button(action_buttons, self.t('clear_log'), self.clear_log, 'secondary', 14, 10)
        self.btn_clear.pack(side=tk.LEFT)
        
        progress_frame = tk.Frame(action_container, bg=self.colors['surface'])
        progress_frame.grid(row=0, column=1, sticky='ew', padx=(18, 0))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', style='App.Horizontal.TProgressbar')
        self.progress.grid(row=0, column=0, sticky='ew')
        
        self.status_bar = tk.Label(
            self.root,
            text=self.t('status_ready'),
            bd=0,
            anchor=tk.W,
            font=('Segoe UI', 9),
            bg=self.colors['dark'],
            fg='white',
            padx=14,
            pady=6
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, before=action_container)
        
        self.log(self.t('welcome'), 'info')
        self.log(self.t('select_folder'), 'info')
    
    def toggle_backup(self):
        self.create_backups = self.backup_var.get()
        msg = "Backup datoteke će biti kreirane" if self.create_backups else "Backup datoteke neće biti kreirane"
        if self.language == 'en':
            msg = "Backup files will be created" if self.create_backups else "Backup files will not be created"
        self.log(msg, 'info')
    
    def show_cleaned_files(self):
        if not self.cleaned_files:
            title = "Očišćene datoteke" if self.language == 'hr' else "Cleaned Files"
            msg = "Nema očišćenih datoteka za prikaz." if self.language == 'hr' else "No cleaned files to display."
            messagebox.showinfo(title, msg)
            return
        
        # Create new window
        window = tk.Toplevel(self.root)
        title = "Očišćene datoteke" if self.language == 'hr' else "Cleaned files"
        window.title(title)
        window.geometry("700x500")
        window.configure(bg=self.colors['background'])
        
        # Header
        header = tk.Label(window, text=title, font=("Segoe UI", 16, "bold"),
                         bg=self.colors['surface'], fg=self.colors['text'],
                         padx=18, pady=14, anchor=tk.W)
        header.pack(fill=tk.X)
        
        # List
        frame = self.make_panel(window, padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        
        text_widget = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bg='#fbfdff',
            fg=self.colors['text'],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        for i, file_info in enumerate(self.cleaned_files, 1):
            text_widget.insert(tk.END, f"{i}. {file_info['name']}\n", 'filename')
            text_widget.insert(tk.END, f"   Uklonjeno blokova: {file_info['removed']}\n\n", 'info')
        
        text_widget.tag_config('filename', foreground=self.colors['success'], font=("Consolas", 10, "bold"))
        text_widget.tag_config('info', foreground="#555")
        text_widget.config(state=tk.DISABLED)
    
    def show_clean_files(self):
        if not self.already_clean_files:
            title = "Čiste datoteke" if self.language == 'hr' else "Clean Files"
            msg = "Nema čistih datoteka za prikaz." if self.language == 'hr' else "No clean files to display."
            messagebox.showinfo(title, msg)
            return
        
        # Create new window
        window = tk.Toplevel(self.root)
        title = "Već čiste datoteke" if self.language == 'hr' else "Already clean files"
        window.title(title)
        window.geometry("700x500")
        window.configure(bg=self.colors['background'])
        
        # Header
        header = tk.Label(window, text=title, font=("Segoe UI", 16, "bold"),
                         bg=self.colors['surface'], fg=self.colors['text'],
                         padx=18, pady=14, anchor=tk.W)
        header.pack(fill=tk.X)
        
        # List
        frame = self.make_panel(window, padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        
        text_widget = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            bg='#fbfdff',
            fg=self.colors['text'],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        for i, filename in enumerate(self.already_clean_files, 1):
            text_widget.insert(tk.END, f"{i}. {filename}\n", 'filename')
        
        text_widget.tag_config('filename', foreground=self.colors['warning'], font=("Consolas", 10, "bold"))
        text_widget.config(state=tk.DISABLED)
    
    def show_removed_blocks(self):
        if not self.removed_blocks_details:
            title = "Uklonjeni blokovi" if self.language == 'hr' else "Removed Blocks"
            msg = "Nema uklonjenih blokova za prikaz." if self.language == 'hr' else "No removed blocks to display."
            messagebox.showinfo(title, msg)
            return
        
        # Create new window
        window = tk.Toplevel(self.root)
        title = "Uklonjeni blokovi" if self.language == 'hr' else "Removed blocks"
        window.title(title)
        window.geometry("800x600")
        window.configure(bg=self.colors['background'])
        
        # Header
        header = tk.Label(window, text=title, font=("Segoe UI", 16, "bold"),
                         bg=self.colors['surface'], fg=self.colors['text'],
                         padx=18, pady=14, anchor=tk.W)
        header.pack(fill=tk.X)
        
        # List
        frame = self.make_panel(window, padx=16, pady=16)
        frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)
        
        text_widget = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            bg='#fbfdff',
            fg=self.colors['text'],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        for filename, blocks in self.removed_blocks_details.items():
            text_widget.insert(tk.END, f"\n{'='*80}\n", 'separator')
            text_widget.insert(tk.END, f"{filename}\n", 'filename')
            text_widget.insert(tk.END, f"{'='*80}\n\n", 'separator')
            
            for block in blocks:
                text_widget.insert(tk.END, f"Blok #{block['number']}  |  {block['timestamp']}\n", 'header')
                text_widget.insert(tk.END, f"{block['text']}\n\n", 'content')
                text_widget.insert(tk.END, f"{'-'*80}\n\n", 'separator')
        
        text_widget.tag_config('filename', foreground=self.colors['danger'], font=("Consolas", 11, "bold"))
        text_widget.tag_config('header', foreground=self.colors['primary'], font=("Consolas", 9, "bold"))
        text_widget.tag_config('content', foreground="#333")
        text_widget.tag_config('separator', foreground="#999")
        text_widget.config(state=tk.DISABLED)
    
    def log(self, message, tag=''):
        if not self.is_ui_thread():
            self.run_on_ui_thread(self.log, message, tag)
            return
        
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        self.log_text.delete('1.0', tk.END)
        self.reset_stats()
        self.cleaned_files = []
        self.already_clean_files = []
        self.error_files = []
        self.removed_blocks_details = {}
    
    def reset_stats(self):
        for key in self.stats:
            self.update_stat(key, 0)
    
    def update_stat(self, key, value=None):
        if value is None:
            self.stats[key] += 1
        else:
            self.stats[key] = value
        
        if not self.is_ui_thread():
            self.run_on_ui_thread(self.update_stat_label, key)
            return
        
        self.update_stat_label(key)
    
    def update_stat_label(self, key):
        self.stat_labels[key].config(text=str(self.stats[key]))
    
    def set_status(self, text):
        if not self.is_ui_thread():
            self.run_on_ui_thread(self.set_status, text)
            return
        
        self.status_bar.config(text=text)
    
    def set_progress(self, value):
        if not self.is_ui_thread():
            self.run_on_ui_thread(self.set_progress, value)
            return
        
        self.progress['value'] = value
    
    def browse_folder(self):
        title = "Odaberi folder s .srt datotekama" if self.language == 'hr' else "Select folder with .srt files"
        folder = filedialog.askdirectory(title=title)
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder, fg=self.colors['dark'])
            self.scan_folder()
    
    def scan_folder(self):
        if not self.selected_folder:
            return
        
        directory = Path(self.selected_folder)
        try:
            self.srt_files = sorted(
                (
                    path for path in directory.rglob("*")
                    if path.is_file() and path.suffix.lower() == ".srt"
                ),
                key=lambda path: str(path).lower()
            )
        except OSError as e:
            self.srt_files = []
            self.update_stat('total', 0)
            msg = f"Greška pri skeniranju foldera: {e}" if self.language == 'hr' else f"Folder scan error: {e}"
            self.log(msg, 'error')
            status = "Greška pri skeniranju foldera." if self.language == 'hr' else "Folder scan error."
            self.set_status(status)
            return
        
        if not self.srt_files:
            self.update_stat('total', 0)
            msg = f"Nema .srt datoteka u folderu: {self.selected_folder}" if self.language == 'hr' else f"No .srt files in folder: {self.selected_folder}"
            self.log(msg, 'warning')
            status = "Nema .srt datoteka u odabranom folderu." if self.language == 'hr' else "No .srt files in selected folder."
            self.set_status(status)
        else:
            msg = f"Pronađeno {len(self.srt_files)} .srt datoteka/e" if self.language == 'hr' else f"Found {len(self.srt_files)} .srt file(s)"
            self.log(msg, 'success')
            status = f"Pronađeno {len(self.srt_files)} .srt datoteka/e. Klikni 'Pokreni Čišćenje'." if self.language == 'hr' else f"Found {len(self.srt_files)} .srt file(s). Click 'Start Cleaning'."
            self.set_status(status)
            self.update_stat('total', len(self.srt_files))
    
    def update_keywords(self):
        text = self.keywords_text.get('1.0', tk.END).strip()
        self.keywords = [kw.strip() for kw in text.split(',') if kw.strip()]
        msg = f"Ažurirano {len(self.keywords)} ključnih riječi" if self.language == 'hr' else f"Updated {len(self.keywords)} keywords"
        self.log(msg, 'success')
        title = "Uspjeh" if self.language == 'hr' else "Success"
        msg_box = f"Ažurirano {len(self.keywords)} ključnih riječi." if self.language == 'hr' else f"Updated {len(self.keywords)} keywords."
        messagebox.showinfo(title, msg_box)
    
    def reset_keywords(self):
        self.keywords = DEFAULT_KEYWORDS.copy()
        self.keywords_text.delete('1.0', tk.END)
        self.keywords_text.insert('1.0', ', '.join(self.keywords))
        msg = "Vraćene zadane ključne riječi" if self.language == 'hr' else "Reset to default keywords"
        self.log(msg, 'info')
    
    def start_cleaning(self):
        if self.is_processing:
            msg = "Obrada je već u tijeku!" if self.language == 'hr' else "Processing already in progress!"
            title = "Upozorenje" if self.language == 'hr' else "Warning"
            messagebox.showwarning(title, msg)
            return
        
        if not self.srt_files:
            msg = "Nema datoteka za obradu!" if self.language == 'hr' else "No files to process!"
            title = "Upozorenje" if self.language == 'hr' else "Warning"
            messagebox.showwarning(title, msg)
            return
        
        # Reset stats and details
        self.update_stat('total', len(self.srt_files))
        self.update_stat('cleaned', 0)
        self.update_stat('already_clean', 0)
        self.update_stat('errors', 0)
        self.update_stat('blocks_removed', 0)
        self.cleaned_files = []
        self.already_clean_files = []
        self.error_files = []
        self.removed_blocks_details = {}
        
        self.is_processing = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_browse.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.progress['maximum'] = len(self.srt_files)
        
        self.log("\n" + "="*80, 'info')
        msg = "Započinjem obradu..." if self.language == 'hr' else "Starting processing..."
        self.log(msg, 'info')
        self.log("="*80 + "\n", 'info')
        
        # Run in thread to avoid freezing UI
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()
    
    def process_files(self):
        for i, srt_file in enumerate(self.srt_files, 1):
            msg = f"\n[{i}/{len(self.srt_files)}] Obrađujem: {srt_file.name}" if self.language == 'hr' else f"\n[{i}/{len(self.srt_files)}] Processing: {srt_file.name}"
            self.log(msg, 'info')
            status = f"Obrađujem: {srt_file.name} ({i}/{len(self.srt_files)})" if self.language == 'hr' else f"Processing: {srt_file.name} ({i}/{len(self.srt_files)})"
            self.set_status(status)
            
            try:
                result = self.process_srt_file(srt_file)
                if result['status'] == 'cleaned':
                    self.update_stat('cleaned')
                    self.cleaned_files.append({
                        'name': srt_file.name,
                        'removed': result['removed_count']
                    })
                    if result['removed_blocks']:
                        self.removed_blocks_details[srt_file.name] = result['removed_blocks']
                elif result['status'] == 'already_clean':
                    self.update_stat('already_clean')
                    self.already_clean_files.append(srt_file.name)
                elif result['status'] == 'error':
                    self.update_stat('errors')
                    self.error_files.append(srt_file.name)
            except Exception as e:
                msg = f"  Greška: {str(e)}" if self.language == 'hr' else f"  Error: {str(e)}"
                self.log(msg, 'error')
                self.update_stat('errors')
                self.error_files.append(srt_file.name)
            
            self.set_progress(i)
        
        self.finish_processing()
    
    def finish_processing(self):
        if not self.is_ui_thread():
            self.run_on_ui_thread(self.finish_processing)
            return
        
        self.is_processing = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_browse.config(state=tk.NORMAL)
        
        self.log("\n" + "="*80, 'success')
        msg = "OBRADA ZAVRŠENA" if self.language == 'hr' else "PROCESSING COMPLETE"
        self.log(msg, 'success')
        self.log("="*80, 'success')
        
        stats_title = "Statistika:" if self.language == 'hr' else "Statistics:"
        self.log(stats_title, 'info')
        
        if self.language == 'hr':
            self.log(f"   • Ukupno: {self.stats['total']}", 'info')
            self.log(f"   • Očišćeno: {self.stats['cleaned']}", 'success')
            self.log(f"   • Već čisto: {self.stats['already_clean']}", 'warning')
            self.log(f"   • Uklonjeno blokova: {self.stats['blocks_removed']}", 'info')
            self.log(f"   • Greške: {self.stats['errors']}", 'error')
            self.log("\nKlikni na statistiku za detalje.", 'info')
            status = "Obrada završena! Provjerite dnevnik za detalje."
            msg_box = (f"Obrada završena!\n\n"
                      f"Očišćeno: {self.stats['cleaned']}\n"
                      f"Već čisto: {self.stats['already_clean']}\n"
                      f"Uklonjeno blokova: {self.stats['blocks_removed']}\n"
                      f"Greške: {self.stats['errors']}\n\n"
                      f"Klikni na statistiku za detalje.")
            title = "Gotovo"
        else:
            self.log(f"   • Total: {self.stats['total']}", 'info')
            self.log(f"   • Cleaned: {self.stats['cleaned']}", 'success')
            self.log(f"   • Already clean: {self.stats['already_clean']}", 'warning')
            self.log(f"   • Blocks removed: {self.stats['blocks_removed']}", 'info')
            self.log(f"   • Errors: {self.stats['errors']}", 'error')
            self.log("\nClick on statistics for details.", 'info')
            status = "Processing complete! Check log for details."
            msg_box = (f"Processing complete!\n\n"
                      f"Cleaned: {self.stats['cleaned']}\n"
                      f"Already clean: {self.stats['already_clean']}\n"
                      f"Blocks removed: {self.stats['blocks_removed']}\n"
                      f"Errors: {self.stats['errors']}\n\n"
                      f"Click on statistics for details.")
            title = "Done"
        
        self.status_bar.config(text=status)
        messagebox.showinfo(title, msg_box)
    
    def process_srt_file(self, filepath):
        blocks = self.parse_srt_file(filepath)
        if not blocks:
            msg = "  Prazna datoteka ili nema valjanih blokova" if self.language == 'hr' else "  Empty file or no valid blocks"
            self.log(msg, 'warning')
            return {'status': 'error', 'removed_count': 0, 'removed_blocks': []}
        
        cleaned, removed_count, removed_blocks = self.clean_srt_blocks(blocks)
        
        if len(cleaned) == len(blocks):
            msg = "  Datoteka već čista" if self.language == 'hr' else "  File already clean"
            self.log(msg, 'success')
            return {'status': 'already_clean', 'removed_count': 0, 'removed_blocks': []}
        
        self.update_stat('blocks_removed', self.stats['blocks_removed'] + removed_count)
        cleaned = self.renumber_blocks(cleaned)
        
        # Create backup if enabled
        original_file = Path(filepath)
        original_encoding = blocks[0].get('original_encoding', 'utf-8')
        if self.create_backups:
            backup_file = self.get_backup_path(original_file)
            shutil.copy2(original_file, backup_file)
            backup_msg = f" (backup: {backup_file.name})" if self.language == 'hr' else f" (backup: {backup_file.name})"
        else:
            backup_msg = ""
        
        # Write cleaned file
        self.write_srt_file(cleaned, original_file, original_encoding)
        
        if self.language == 'hr':
            msg = f"  Očišćeno. Uklonjeno {removed_count} blokova{backup_msg}"
        else:
            msg = f"  Cleaned. Removed {removed_count} blocks{backup_msg}"
        self.log(msg, 'success')
        
        return {'status': 'cleaned', 'removed_count': removed_count, 'removed_blocks': removed_blocks}
    
    def try_encodings(self, filepath):
        encodings = [
            'utf-8-sig',
            'utf-8',
            'cp1250',
            'windows-1250',
            'iso-8859-2',
            'windows-1252',
            'iso-8859-1'
        ]
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as file:
                    content = file.read()
                return content, encoding
            except UnicodeError:
                continue
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        return content, 'utf-8'
    
    def parse_srt_file(self, filepath):
        content, used_encoding = self.try_encodings(filepath)
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        blocks = re.split(r'\n\s*\n', content.strip())
        parsed_blocks = []
        for block in blocks:
            if block.strip():
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    try:
                        number = int(lines[0].strip().lstrip('\ufeff'))
                        timestamp = lines[1].strip()
                        text = '\n'.join(lines[2:])
                        parsed_blocks.append({
                            'number': number,
                            'timestamp': timestamp,
                            'text': text,
                            'original_encoding': used_encoding
                        })
                    except ValueError:
                        continue
        return parsed_blocks
    
    def clean_srt_blocks(self, blocks):
        cleaned = []
        removed_blocks = []
        removed_count = 0
        
        for block in blocks:
            text_lower = block['text'].lower()
            should_remove = any(keyword.lower() in text_lower for keyword in self.keywords)
            
            if not should_remove:
                cleaned.append(block)
            else:
                removed_count += 1
                removed_blocks.append(block)
        
        return cleaned, removed_count, removed_blocks
    
    def renumber_blocks(self, blocks):
        for i, block in enumerate(blocks, 1):
            block['number'] = i
        return blocks
    
    def get_backup_path(self, original_file):
        backup_file = original_file.with_suffix(original_file.suffix + ".bak")
        if not backup_file.exists():
            return backup_file
        
        counter = 1
        while True:
            candidate = original_file.with_name(f"{original_file.name}.bak.{counter}")
            if not candidate.exists():
                return candidate
            counter += 1
    
    def get_output_encoding(self, original_encoding):
        safe_encodings = [
            'utf-8',
            'utf-8-sig',
            'cp1250',
            'windows-1250',
            'iso-8859-2',
            'windows-1252',
            'iso-8859-1'
        ]
        if original_encoding in safe_encodings:
            return original_encoding
        return 'utf-8'
    
    def write_srt_temp_file(self, blocks, target_path, encoding):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                'w',
                encoding=encoding,
                newline='\n',
                dir=target_path.parent,
                prefix=f".{target_path.name}.",
                suffix=".tmp",
                delete=False
            ) as file:
                temp_path = Path(file.name)
                for i, block in enumerate(blocks):
                    file.write(f"{block['number']}\n{block['timestamp']}\n{block['text']}\n")
                    if i < len(blocks) - 1:
                        file.write('\n')
            return temp_path
        except Exception:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise
    
    def write_srt_file(self, blocks, filepath, original_encoding='utf-8'):
        filepath = Path(filepath)
        output_encoding = self.get_output_encoding(original_encoding)
        temp_path = None
        try:
            temp_path = self.write_srt_temp_file(blocks, filepath, output_encoding)
        except UnicodeEncodeError:
            temp_path = self.write_srt_temp_file(blocks, filepath, 'utf-8')
        
        try:
            os.replace(temp_path, filepath)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()


def main():
    root = tk.Tk()
    app = SRTCleanerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
