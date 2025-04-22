import cloudscraper
import json
import time
import os
import csv
import pandas as pd
import re
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from tkinter.font import Font
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, Counter
import sys

# Add debug print statements
print("Script started")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# Check if matplotlib is available
try:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    print("Matplotlib imported successfully")
except ImportError as e:
    print(f"Error importing matplotlib: {e}")


    # Create a fallback for the visualizer
    class FigureCanvasTkAgg:
        def __init__(self, fig, master):
            self.master = master

        def get_tk_widget(self):
            label = tk.Label(self.master, text="Matplotlib not available. Install with: pip install matplotlib")
            return label


# Simple class for handling card visualization without matplotlib dependency
class SimpleCardVisualizer:
    def __init__(self, output_dir="moxfield_data"):
        self.output_dir = output_dir
        self.analysis_dir = f"{output_dir}/analysis"
        self.all_cards = None
        self.recommended_deck = None

    def process_mana_symbols(self, mana_cost):
        """Replace mana symbols with text representation"""
        if not mana_cost or not isinstance(mana_cost, str):
            return mana_cost

        # Replace mana symbols with simple text
        mana_cost = mana_cost.replace("{R}", "R")
        mana_cost = mana_cost.replace("{W}", "W")
        mana_cost = mana_cost.replace("{B}", "B")
        mana_cost = mana_cost.replace("{U}", "U")
        mana_cost = mana_cost.replace("{G}", "G")

        return mana_cost

    def load_data(self):
        """Load the analysis data files"""
        all_cards_path = f"{self.analysis_dir}/all_cards_analysis.csv"
        deck_path = f"{self.analysis_dir}/recommended_decklist.csv"

        if os.path.exists(all_cards_path):
            self.all_cards = pd.read_csv(all_cards_path)
        else:
            self.all_cards = None

        if os.path.exists(deck_path):
            self.recommended_deck = pd.read_csv(deck_path)
        else:
            self.recommended_deck = None

        return self.all_cards is not None and self.recommended_deck is not None

    def create_text_summary(self, parent_widget):
        """Create a text summary of the analyzed data"""
        if not self.load_data():
            text = tk.Text(parent_widget, height=20, width=80)
            text.insert(tk.END, "No data found. Run analysis first.")
            return text

        text = tk.Text(parent_widget, height=20, width=80)

        # Configure tags for colorization
        text.tag_configure("header", font=("Helvetica", 12, "bold"))
        text.tag_configure("owned", foreground="green")
        text.tag_configure("not_owned", foreground="red")
        text.tag_configure("auto_include", background="#ffff99")

        # Configure mana symbol tags with colored backgrounds
        text.tag_configure("mana_r", foreground="white", background="red")
        text.tag_configure("mana_w", foreground="black", background="white")
        text.tag_configure("mana_b", foreground="white", background="black")
        text.tag_configure("mana_u", foreground="white", background="blue")
        text.tag_configure("mana_g", foreground="white", background="green")

        # Summary of all cards
        owned_cards = self.all_cards[self.all_cards['Owned'] == True]
        text.insert(tk.END, "CARD ANALYSIS SUMMARY\n", "header")
        text.insert(tk.END, f"{'-' * 50}\n\n")
        text.insert(tk.END, f"Total unique cards found: {len(self.all_cards)}\n")
        text.insert(tk.END,
                    f"Cards you own: {len(owned_cards)} ({len(owned_cards) / len(self.all_cards) * 100:.1f}%)\n\n")

        text.insert(tk.END, "Top 10 Most Common Cards:\n")
        top_cards = self.all_cards.sort_values('Deck Count', ascending=False).head(10)
        for i, (_, row) in enumerate(top_cards.iterrows(), 1):
            owned = row.get('Owned', False)
            tag = "owned" if owned else "not_owned"
            owned_text = "✓" if owned else "✗"
            card_name = row['Card Name']
            mana_cost = row.get('Mana Cost', '')

            # Insert the card name and basic info
            text.insert(tk.END, f"{i}. {card_name} ", tag)

            # Insert mana symbols if present
            if mana_cost:
                self.insert_mana_symbols(text, mana_cost)

            # Insert the rest of the info
            text.insert(tk.END, f" ({row['Deck Count']} decks) {owned_text}\n", tag)

        text.insert(tk.END, f"\n\nRECOMMENDED DECK SUMMARY\n", "header")
        text.insert(tk.END, f"{'-' * 50}\n\n")

        # Count auto-include cards
        auto_include_cards = self.recommended_deck[self.recommended_deck['Auto-Include'] == True]
        owned_in_deck = self.recommended_deck[self.recommended_deck['Owned'] == True]

        text.insert(tk.END, f"Deck size: {len(self.recommended_deck)} cards\n")
        text.insert(tk.END, f"Auto-include cards: {len(auto_include_cards)} cards\n")
        text.insert(tk.END,
                    f"Cards you already own: {len(owned_in_deck)} ({len(owned_in_deck) / len(self.recommended_deck) * 100:.1f}%)\n\n")

        text.insert(tk.END, "Top Auto-Include Cards in Recommended Deck:\n")
        auto_includes = self.recommended_deck[self.recommended_deck['Auto-Include'] == True].head(10)
        if len(auto_includes) > 0:
            for i, (_, row) in enumerate(auto_includes.iterrows(), 1):
                owned = row.get('Owned', False)
                owned_text = "✓" if owned else "✗"
                card_name = row['Card Name']
                mana_cost = row.get('Mana Cost', '')

                # Insert the card name with auto-include tag
                text.insert(tk.END, f"{i}. {card_name} ", "auto_include")

                # Insert mana symbols if present
                if mana_cost:
                    self.insert_mana_symbols(text, mana_cost)

                # Insert remaining info with owned/not owned tag
                tag = "owned" if owned else "not_owned"
                text.insert(tk.END, f" ({row['Frequency']} decks) {owned_text}\n", tag)
        else:
            text.insert(tk.END, "No auto-include cards found.\n")

        text.insert(tk.END, "\nTop Regular Cards in Recommended Deck:\n")
        top_deck = self.recommended_deck[self.recommended_deck['Auto-Include'] == False].sort_values('Frequency',
                                                                                                     ascending=False).head(
            10)
        for i, (_, row) in enumerate(top_deck.iterrows(), 1):
            owned = row.get('Owned', False)
            owned_text = "✓" if owned else "✗"
            tag = "owned" if owned else "not_owned"
            card_name = row['Card Name']
            mana_cost = row.get('Mana Cost', '')

            # Insert the card name
            text.insert(tk.END, f"{i}. {card_name} ", tag)

            # Insert mana symbols if present
            if mana_cost:
                self.insert_mana_symbols(text, mana_cost)

            # Insert the rest of the info
            text.insert(tk.END, f" ({row['Frequency']} decks) {owned_text}\n", tag)

        return text

    def insert_mana_symbols(self, text_widget, mana_cost):
        """Insert mana symbols into the text widget with appropriate tags"""
        if not mana_cost or not isinstance(mana_cost, str):
            return

        i = 0
        while i < len(mana_cost):
            if i + 2 < len(mana_cost) and mana_cost[i:i + 3] == "{R}":
                text_widget.insert(tk.END, "R", "mana_r")
                i += 3
            elif i + 2 < len(mana_cost) and mana_cost[i:i + 3] == "{W}":
                text_widget.insert(tk.END, "W", "mana_w")
                i += 3
            elif i + 2 < len(mana_cost) and mana_cost[i:i + 3] == "{B}":
                text_widget.insert(tk.END, "B", "mana_b")
                i += 3
            elif i + 2 < len(mana_cost) and mana_cost[i:i + 3] == "{U}":
                text_widget.insert(tk.END, "U", "mana_u")
                i += 3
            elif i + 2 < len(mana_cost) and mana_cost[i:i + 3] == "{G}":
                text_widget.insert(tk.END, "G", "mana_g")
                i += 3
            elif i < len(mana_cost) and mana_cost[i] == "{":
                # Handle other mana symbols (like colorless)
                closing_idx = mana_cost.find("}", i)
                if closing_idx != -1:
                    text_widget.insert(tk.END, mana_cost[i + 1:closing_idx])
                    i = closing_idx + 1
                else:
                    text_widget.insert(tk.END, mana_cost[i])
                    i += 1
            else:
                text_widget.insert(tk.END, mana_cost[i])
                i += 1

    def process_mana_symbols(self, mana_cost):
        """Replace mana symbols with formatted text - this is kept for compatibility
           but the actual rendering is now done directly in the text widget"""
        if not mana_cost or not isinstance(mana_cost, str):
            return mana_cost

        # Replace mana symbols with letter representations
        mana_cost = mana_cost.replace("{R}", "R")
        mana_cost = mana_cost.replace("{W}", "W")
        mana_cost = mana_cost.replace("{B}", "B")
        mana_cost = mana_cost.replace("{U}", "U")
        mana_cost = mana_cost.replace("{G}", "G")

        return mana_cost


# Main application class
class MoxfieldAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MTG Deck Analyzer")
        self.root.geometry("1200x800")  # Increase default size
        self.root.minsize(1000, 700)  # Set minimum window size
        self.root.configure(bg="#f0f0f0")

        # Enable debug mode
        self.debug_mode = True

        print("Initializing analyzer app")

        # Initialize analyzer
        self.analyzer = MoxfieldAnalyzer()

        # Initialize visualizer
        self.visualizer = None

        # Initialize auto-include manager
        self.auto_include_manager = AutoIncludeManager()

        # Initialize variables that will be set up later
        self.auto_include_color_var = tk.StringVar(value="WHITE")
        self.card_name_var = tk.StringVar()
        self.auto_include_list = None
        self.color_vars = {}
        self.log_text = None
        self.mana_color_frames = []  # Add this line to store color frames

        # Initialize sort variables
        self.sort_column = "Rank"  # Default sort column
        self.sort_ascending = False  # Default sort direction

        # Set up the GUI elements
        self.setup_ui()

        # Make sure window appears on top
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)

        print("App initialization complete")

    def process_mana_symbols(self, mana_cost):
        """Convert mana symbols to formatted text for display"""
        if not mana_cost or not isinstance(mana_cost, str):
            return mana_cost

        # Create a text representation using Unicode circle symbols
        # This will be displayed in the treeview
        processed = ""
        i = 0
        while i < len(mana_cost):
            if i + 2 < len(mana_cost):
                if mana_cost[i:i + 3] == "{R}":
                    processed += "(R)"  # Red mana
                    i += 3
                    continue
                elif mana_cost[i:i + 3] == "{W}":
                    processed += "(W)"  # White mana
                    i += 3
                    continue
                elif mana_cost[i:i + 3] == "{B}":
                    processed += "(B)"  # Black mana
                    i += 3
                    continue
                elif mana_cost[i:i + 3] == "{U}":
                    processed += "(U)"  # Blue mana
                    i += 3
                    continue
                elif mana_cost[i:i + 3] == "{G}":
                    processed += "(G)"  # Green mana
                    i += 3
                    continue

            # Handle other characters
            if i < len(mana_cost):
                if mana_cost[i] == "{":
                    # Handle other mana symbols (like colorless)
                    closing_idx = mana_cost.find("}", i)
                    if closing_idx != -1:
                        processed += f"({mana_cost[i + 1:closing_idx]})"
                        i = closing_idx + 1
                    else:
                        processed += mana_cost[i]
                        i += 1
                else:
                    processed += mana_cost[i]
                    i += 1

        return processed

    def add_auto_include(self):
        """Add a card to auto-includes for the selected color"""
        color = self.auto_include_color_var.get()
        card_name = self.card_name_var.get().strip()

        if card_name:
            if self.auto_include_manager.add_auto_include(color, card_name):
                self.update_auto_include_list()
                self.card_name_var.set("")
                self.log(f"Added {card_name} to {color} auto-includes")
            else:
                self.log(f"Card {card_name} already in {color} auto-includes")

    def remove_auto_include(self):
        """Remove selected card from auto-includes"""
        color = self.auto_include_color_var.get()
        selected_cards = [card for card, var in self.checkbox_vars.items() if var.get()]

        if not selected_cards:
            self.log("No card selected for removal")
            print("No card was selected in the auto-include list")
            return

        selected_card = selected_cards[0]
        # Debug information
        print(f"Removing card: '{selected_card}' from color: '{color}'")
        print(f"Before removal, {color} has: {self.auto_include_manager.auto_includes.get(color, [])}")

        if self.auto_include_manager.remove_auto_include(color, selected_card):
            self.update_auto_include_list()
            self.log(f"Removed {selected_card} from {color} auto-includes")
            print(f"After removal, {color} has: {self.auto_include_manager.auto_includes.get(color, [])}")
        else:
            self.log(f"Failed to remove {selected_card} from {color} auto-includes")
            print(f"Removal failed. Color or card might not exist in auto_includes dictionary")

    def update_auto_include_list(self):
        """Update the list of auto-include cards for the selected color"""
        # Clear existing checkboxes
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()
        self.card_type_vars.clear()

        color = self.auto_include_color_var.get()

        # Debug output about files
        print(f"DEBUG: Using auto_include_file: {self.auto_include_manager.auto_include_file}")
        print(f"DEBUG: Using disabled_file: {self.auto_include_manager.disabled_file}")

        # Normalize the color to ensure consistent lookup
        original_color = color
        color = self.auto_include_manager.normalize_color_pair(color)
        if original_color != color:
            print(f"Normalized color from '{original_color}' to '{color}' for consistent lookup")

        # Debug current selection
        print(f"Updating auto-include list for selected color: {color}")

        # Special debug for BLUE_BLACK
        if original_color == "BLUE_BLACK" or color == "BLUE_BLACK" or color == "BLACK_BLUE":
            print("DEBUG: Processing BLUE_BLACK in UI update:")
            print(f"  - All auto_include keys: {list(self.auto_include_manager.auto_includes.keys())}")
            print(f"  - 'BLUE_BLACK' exists? {'BLUE_BLACK' in self.auto_include_manager.auto_includes}")
            print(f"  - 'BLACK_BLUE' exists? {'BLACK_BLUE' in self.auto_include_manager.auto_includes}")
            if 'BLUE_BLACK' in self.auto_include_manager.auto_includes:
                print(f"  - Cards in BLUE_BLACK: {self.auto_include_manager.auto_includes['BLUE_BLACK']}")
            if 'BLACK_BLUE' in self.auto_include_manager.auto_includes:
                print(f"  - Cards in BLACK_BLUE: {self.auto_include_manager.auto_includes['BLACK_BLUE']}")

        # Check if this color exists in auto_includes
        if color in self.auto_include_manager.auto_includes:
            cards = self.auto_include_manager.auto_includes[color]
            print(f"Found {len(cards)} cards for {color}: {cards}")
            for card in cards:
                self.auto_include_list.insert(tk.END, card)
        else:
            print(f"WARNING: Color {color} not found in auto_includes dictionary!")

    def get_selected_colors(self):
        """Get list of selected colors"""
        return [color for color, var in self.color_vars.items() if var.get()]

    def setup_ui(self):
        # Add padding around all frames
        padx = 10
        pady = 5

        print("Setting up UI")

        # Title
        title_frame = tk.Frame(self.root, bg="#f0f0f0")
        title_frame.pack(fill="x", padx=padx, pady=pady)

        title_label = tk.Label(
            title_frame,
            text="MTG Deck Analyzer",
            font=Font(family="Helvetica", size=18, weight="bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=10)

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=padx, pady=pady)

        # Create tabs
        self.setup_tab = tk.Frame(self.notebook, bg="#f0f0f0")
        self.results_tab = tk.Frame(self.notebook, bg="#f0f0f0")
        self.visualization_tab = tk.Frame(self.notebook, bg="#f0f0f0")

        self.notebook.add(self.setup_tab, text="Setup & Run")
        self.notebook.add(self.results_tab, text="Results")
        self.notebook.add(self.visualization_tab, text="Visualization")

        # Setup the content for each tab
        self.setup_setup_tab()
        self.setup_results_tab()
        self.setup_visualization_tab()

        print("UI setup complete")

    def setup_setup_tab(self):
        # Input section
        self.setup_tab.rowconfigure(0, weight=0)  # Input frame - fixed size
        self.setup_tab.rowconfigure(1, weight=0)  # Action frame - fixed size
        self.setup_tab.rowconfigure(2, weight=0)  # Progress frame - fixed size
        self.setup_tab.rowconfigure(3, weight=1)  # Log frame - expands to fill space
        self.setup_tab.columnconfigure(0, weight=1)  # All frames expand horizontally

        input_frame = tk.LabelFrame(self.setup_tab, text="Input Settings", padx=10, pady=10, bg="#f0f0f0")
        input_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # CSV file selection
        csv_frame = tk.Frame(input_frame, bg="#f0f0f0")
        csv_frame.pack(fill="x", padx=10, pady=5)

        csv_label = tk.Label(csv_frame, text="Card Collection CSV:", bg="#f0f0f0")
        csv_label.pack(side="left", padx=5)

        self.csv_path_var = tk.StringVar()
        csv_entry = tk.Entry(csv_frame, textvariable=self.csv_path_var, width=50)
        csv_entry.pack(side="left", padx=5, fill="x", expand=True)

        csv_button = tk.Button(
            csv_frame,
            text="Browse",
            command=self.browse_csv_file,
            bg="#e0e0e0"
        )
        csv_button.pack(side="left", padx=5)

        # Commander selection
        commander_frame = tk.Frame(input_frame, bg="#f0f0f0")
        commander_frame.pack(fill="x", padx=10, pady=5)

        commander_label = tk.Label(commander_frame, text="Commander ID:", bg="#f0f0f0")
        commander_label.pack(side="left", padx=5)

        self.commander_var = tk.StringVar(value="kq6Nz")  # Default to Gyome
        commander_entry = tk.Entry(commander_frame, textvariable=self.commander_var, width=10)
        commander_entry.pack(side="left", padx=5)

        commander_info = tk.Label(
            commander_frame,
            text="(Default: kq6Nz for Gyome, Master Chef. Add multiple IDs separated by commas)",
            bg="#f0f0f0"
        )
        commander_info.pack(side="left", padx=5)

        # Add help button for commander ID lookup instructions
        def show_commander_id_help():
            help_text = (
                "To find commander ID:\n"
                "1. Go to Moxfield.com\n"
                "2. Open network tab (right click + inspect, network)\n"
                "3. Select FETCH/XHR and type in cardID in filter\n"
                "4. Open Advanced filters for decksearch, select commander and save filters\n"
                "5. API request now shows up and should look like: \n"
                "https://api2.moxfield.com/v2/decks/search-sfw?pageNumber=1&pageSize=64&sortType=updated&sortDirection=descending&commanderCardId=J9WQA\n"
                "6. In this example: J9WQA is your commander ID"
            )

            help_window = tk.Toplevel(self.root)
            help_window.title("How to Find Commander ID")
            help_window.geometry("700x250")
            help_window.resizable(True, True)
            help_window.configure(bg="#f0f0f0")

            # Make window modal
            help_window.transient(self.root)
            help_window.grab_set()

            # Add text widget to display the help text
            text = tk.Text(help_window, wrap="word", bg="#f0f0f0", padx=10, pady=10)
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.insert("1.0", help_text)
            text.config(state="disabled")  # Make text read-only

            # Add close button
            close_button = tk.Button(
                help_window,
                text="Close",
                command=help_window.destroy,
                bg="#e0e0e0"
            )
            close_button.pack(pady=10)

            # Center the window relative to the main window
            help_window.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - help_window.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - help_window.winfo_height()) // 2
            help_window.geometry(f"+{x}+{y}")

        help_button = tk.Button(
            commander_frame,
            text="?",
            command=show_commander_id_help,
            bg="#e0e0e0",
            width=2,
            height=1,
            font=("Helvetica", 10, "bold")
        )
        help_button.pack(side="left", padx=5)

        # Add page limit input for deck scraping
        page_limit_frame = tk.Frame(commander_frame, bg="#f0f0f0")
        page_limit_frame.pack(side="left", padx=5)

        page_limit_label = tk.Label(page_limit_frame, text="Pages to scrape:", bg="#f0f0f0")
        page_limit_label.pack(side="left")

        self.page_limit_var = tk.IntVar(value=5)  # Default 5 pages
        page_limit_spinbox = tk.Spinbox(
            page_limit_frame,
            from_=1,
            to=50,
            textvariable=self.page_limit_var,
            width=3
        )
        page_limit_spinbox.pack(side="left", padx=2)

        page_info_label = tk.Label(
            page_limit_frame,
            text="(64 decks per page)",
            bg="#f0f0f0",
            font=("Helvetica", 8)
        )
        page_info_label.pack(side="left", padx=2)

        # Color selection
        color_frame = tk.Frame(input_frame, bg="#f0f0f0")
        color_frame.pack(fill="x", padx=10, pady=5)

        color_label = tk.Label(color_frame, text="Commander Colors:", bg="#f0f0f0")
        color_label.pack(side="left", padx=5)

        self.color_vars = {
            "WHITE": tk.BooleanVar(),
            "BLUE": tk.BooleanVar(),
            "BLACK": tk.BooleanVar(),
            "RED": tk.BooleanVar(),
            "GREEN": tk.BooleanVar(),
            "GREY": tk.BooleanVar()
        }

        for color, var in self.color_vars.items():
            cb = tk.Checkbutton(
                color_frame,
                text=color,
                variable=var,
                bg="#f0f0f0"
            )
            cb.pack(side="left", padx=5)

        # Auto-include management
        auto_include_frame = tk.LabelFrame(input_frame, text="Auto-Include Cards", padx=10, pady=10, bg="#f0f0f0")
        auto_include_frame.pack(fill="x", padx=10, pady=5)

        # Color selection for auto-includes
        color_select_frame = tk.Frame(auto_include_frame, bg="#f0f0f0")
        color_select_frame.pack(fill="x", padx=10, pady=5)

        # Create a list of all color combinations for the dropdown
        color_combinations = list(self.color_vars.keys())
        # Add two-color combinations
        two_color_combos = [
            "WHITE_BLUE", "WHITE_BLACK", "WHITE_RED", "WHITE_GREEN",
            "BLUE_BLACK", "BLUE_RED", "BLUE_GREEN",
            "BLACK_RED", "BLACK_GREEN",
            "RED_GREEN"
        ]
        color_combinations.extend(two_color_combos)

        self.auto_include_color_var = tk.StringVar(value="WHITE")
        color_menu = ttk.OptionMenu(
            color_select_frame,
            self.auto_include_color_var,
            "WHITE",
            *color_combinations
        )
        color_menu.pack(side="left", padx=5)

        # Card name entry
        card_frame = tk.Frame(auto_include_frame, bg="#f0f0f0")
        card_frame.pack(fill="x", padx=10, pady=5)

        self.card_name_var = tk.StringVar()
        card_name_label = tk.Label(card_frame, text="Card Name:", bg="#f0f0f0")
        card_name_label.pack(side="left", padx=5)
        card_entry = tk.Entry(card_frame, textvariable=self.card_name_var, width=40)
        card_entry.pack(side="left", padx=5, fill="x", expand=True)

        # Card type selection
        card_type_frame = tk.Frame(auto_include_frame, bg="#f0f0f0")
        card_type_frame.pack(fill="x", padx=10, pady=5)

        card_type_label = tk.Label(card_type_frame, text="Card Type:", bg="#f0f0f0")
        card_type_label.pack(side="left", padx=5)

        self.card_type_var = tk.StringVar(value="Unknown")
        card_types = ["Unknown", "Land", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery"]
        card_type_menu = ttk.Combobox(
            card_type_frame,
            textvariable=self.card_type_var,
            values=card_types,
            state="readonly",
            width=15
        )
        card_type_menu.pack(side="left", padx=5)

        add_button = tk.Button(
            card_type_frame,
            text="Add Card",
            command=self.add_auto_include,
            bg="#e0e0e0"
        )
        add_button.pack(side="left", padx=5)

        # Frame for auto-include list and checkboxes
        list_frame = tk.Frame(auto_include_frame, bg="#f0f0f0")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create a frame for the cards with checkboxes
        self.cards_frame = tk.Frame(list_frame, bg="#f0f0f0")
        self.cards_frame.pack(side="left", fill="both", expand=True)

        # Scrollbar for the cards frame
        cards_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        cards_scrollbar.pack(side="right", fill="y")

        # Add scrollable canvas inside the cards frame
        self.cards_canvas = tk.Canvas(self.cards_frame, bg="#f0f0f0", yscrollcommand=cards_scrollbar.set)
        self.cards_canvas.pack(side="left", fill="both", expand=True)

        # Configure the scrollbar to scroll the canvas
        cards_scrollbar.config(command=self.cards_canvas.yview)

        # Create a frame inside the canvas to hold the checkboxes
        self.checkbox_frame = tk.Frame(self.cards_frame, bg="#f0f0f0")
        self.checkbox_window = self.cards_canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")

        # Configure canvas scrolling
        self.checkbox_frame.bind("<Configure>", self.on_frame_configure)
        self.cards_canvas.bind("<Configure>", self.on_canvas_configure)

        # Dictionary to store checkbox variables
        self.checkbox_vars = {}

        # Dictionary to store card type variables for each card
        self.card_type_vars = {}

        # Button frame
        button_frame = tk.Frame(auto_include_frame, bg="#f0f0f0")
        button_frame.pack(pady=5)

        remove_button = tk.Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_auto_include,
            bg="#e0e0e0"
        )
        remove_button.pack(side="left", padx=5)

        update_button = tk.Button(
            button_frame,
            text="Update Card Types",
            command=self.update_card_types,
            bg="#e0e0e0"
        )
        update_button.pack(side="left", padx=5)

        # Update auto-include list when color changes
        self.auto_include_color_var.trace_add("write", lambda *args: self.update_auto_include_list())

        # Output name
        name_frame = tk.Frame(input_frame, bg="#f0f0f0")
        name_frame.pack(fill="x", padx=10, pady=5)

        name_label = tk.Label(name_frame, text="Output Name:", bg="#f0f0f0")
        name_label.pack(side="left", padx=5)

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.name_var = tk.StringVar(value=f"moxfield_analysis_{current_date}")
        name_entry = tk.Entry(name_frame, textvariable=self.name_var, width=40)
        name_entry.pack(side="left", padx=5, fill="x", expand=True)

        # After color selection, add land count selection
        land_frame = tk.Frame(input_frame, bg="#f0f0f0")
        land_frame.pack(fill="x", padx=10, pady=5)

        land_label = tk.Label(land_frame, text="Land Count:", bg="#f0f0f0")
        land_label.pack(side="left", padx=5)

        self.land_count_var = tk.IntVar(value=37)  # Default land count
        land_count_entry = tk.Spinbox(
            land_frame,
            from_=0,
            to=100,
            textvariable=self.land_count_var,
            width=5
        )
        land_count_entry.pack(side="left", padx=5)

        land_info = tk.Label(
            land_frame,
            text="(Number of lands to include in recommended deck)",
            bg="#f0f0f0"
        )
        land_info.pack(side="left", padx=5)

        # Actions - now using grid
        action_frame = tk.Frame(self.setup_tab, bg="#f0f0f0")
        action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        self.run_button = tk.Button(
            action_frame,
            text="Run Analysis",
            command=self.run_analysis,
            font=Font(family="Helvetica", size=12),
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=5
        )
        self.run_button.pack(side="left", padx=10)

        # Progress section
        progress_frame = tk.LabelFrame(self.setup_tab, text="Progress", padx=10, pady=10, bg="#f0f0f0")
        progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=100
        )
        self.progress_bar.pack(fill="x", padx=10, pady=5)

        # Log section - now using grid and will expand with window
        log_frame = tk.LabelFrame(self.setup_tab, text="Log", padx=10, pady=10, bg="#f0f0f0")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        # Make the log frame content resizable
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

    def on_frame_configure(self, event):
        """Reset the scroll region to encompass the inner frame"""
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """When the canvas changes size, resize the inner frame"""
        self.cards_canvas.itemconfig(self.checkbox_window, width=event.width)

    def update_auto_include_list(self):
        """Update the list of auto-include cards for the selected color"""
        # Clear existing checkboxes
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()
        self.card_type_vars.clear()

        color = self.auto_include_color_var.get()

        # Debug output about files
        print(f"DEBUG: Using auto_include_file: {self.auto_include_manager.auto_include_file}")
        print(f"DEBUG: Using disabled_file: {self.auto_include_manager.disabled_file}")

        # Normalize the color to ensure consistent lookup
        original_color = color
        color = self.auto_include_manager.normalize_color_pair(color)
        if original_color != color:
            print(f"Normalized color from '{original_color}' to '{color}' for consistent lookup")

        # Debug current selection
        print(f"Updating auto-include list for selected color: {color}")

        # Special debug for BLUE_BLACK
        if original_color == "BLUE_BLACK" or color == "BLUE_BLACK" or color == "BLACK_BLUE":
            print("DEBUG: Processing BLUE_BLACK in UI update:")
            print(f"  - All auto_include keys: {list(self.auto_include_manager.auto_includes.keys())}")
            print(f"  - 'BLUE_BLACK' exists? {'BLUE_BLACK' in self.auto_include_manager.auto_includes}")
            print(f"  - 'BLACK_BLUE' exists? {'BLACK_BLUE' in self.auto_include_manager.auto_includes}")
            if 'BLUE_BLACK' in self.auto_include_manager.auto_includes:
                print(f"  - Cards in BLUE_BLACK: {self.auto_include_manager.auto_includes['BLUE_BLACK']}")
            if 'BLACK_BLUE' in self.auto_include_manager.auto_includes:
                print(f"  - Cards in BLACK_BLUE: {self.auto_include_manager.auto_includes['BLACK_BLUE']}")

        # Check if this color exists in auto_includes
        if color in self.auto_include_manager.auto_includes:
            cards = self.auto_include_manager.auto_includes[color]
            print(f"Found {len(cards)} cards for {color}: {cards}")

            # Add a checkbox for each card
            for i, card in enumerate(cards):
                # Create a variable for this checkbox
                var = tk.BooleanVar(value=self.auto_include_manager.is_card_enabled(color, card))
                self.checkbox_vars[card] = var

                # Create a frame for this card entry
                card_entry_frame = tk.Frame(self.checkbox_frame, bg="#f0f0f0")
                card_entry_frame.pack(fill="x", padx=5, pady=2)

                # Add the checkbox
                cb = tk.Checkbutton(
                    card_entry_frame,
                    text="",
                    variable=var,
                    bg="#f0f0f0",
                    command=lambda c=card, v=var: self.toggle_card_enabled(c, v)
                )
                cb.pack(side="left", padx=5)

                # Create a label for the card name
                card_label = tk.Label(
                    card_entry_frame,
                    text=card,
                    width=30,
                    anchor="w",
                    bg="#f0f0f0"
                )
                card_label.pack(side="left", padx=5)

                # Create a dropdown for card type
                card_type = self.auto_include_manager.get_card_type(card)
                type_var = tk.StringVar(value=card_type)
                self.card_type_vars[card] = type_var

                card_types = ["Unknown", "Land", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery"]
                type_menu = ttk.Combobox(
                    card_entry_frame,
                    textvariable=type_var,
                    values=card_types,
                    state="readonly",
                    width=12
                )
                type_menu.pack(side="left", padx=5)

            # Update the canvas scroll region
            self.checkbox_frame.update_idletasks()
            self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))
        else:
            # Try alternate key format for backward compatibility
            if "_" in color:
                parts = color.split("_")
                alternate_key = f"{parts[1]}_{parts[0]}"
                if alternate_key in self.auto_include_manager.auto_includes:
                    print(f"Using alternate key format {alternate_key} instead of {color}")
                    cards = self.auto_include_manager.auto_includes[alternate_key]
                    print(f"Found {len(cards)} cards for {alternate_key}: {cards}")

                    # Add a checkbox for each card
                    for i, card in enumerate(cards):
                        # Create a variable for this checkbox
                        var = tk.BooleanVar(value=self.auto_include_manager.is_card_enabled(alternate_key, card))
                        self.checkbox_vars[card] = var

                        # Create a frame for this card entry
                        card_entry_frame = tk.Frame(self.checkbox_frame, bg="#f0f0f0")
                        card_entry_frame.pack(fill="x", padx=5, pady=2)

                        # Add the checkbox
                        cb = tk.Checkbutton(
                            card_entry_frame,
                            text="",
                            variable=var,
                            bg="#f0f0f0",
                            command=lambda c=card, v=var: self.toggle_card_enabled(c, v)
                        )
                        cb.pack(side="left", padx=5)

                        # Create a label for the card name
                        card_label = tk.Label(
                            card_entry_frame,
                            text=card,
                            width=30,
                            anchor="w",
                            bg="#f0f0f0"
                        )
                        card_label.pack(side="left", padx=5)

                        # Create a dropdown for card type
                        card_type = self.auto_include_manager.get_card_type(card)
                        type_var = tk.StringVar(value=card_type)
                        self.card_type_vars[card] = type_var

                        card_types = ["Unknown", "Land", "Creature", "Artifact", "Enchantment", "Instant", "Sorcery"]
                        type_menu = ttk.Combobox(
                            card_entry_frame,
                            textvariable=type_var,
                            values=card_types,
                            state="readonly",
                            width=12
                        )
                        type_menu.pack(side="left", padx=5)

                    # Update the canvas scroll region
                    self.checkbox_frame.update_idletasks()
                    self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))
                    return

            print(f"WARNING: Color {color} not found in auto_includes dictionary!")

    def update_card_types(self):
        """Update card types for all cards in the current view"""
        color = self.auto_include_color_var.get()
        updated_count = 0

        for card, type_var in self.card_type_vars.items():
            new_type = type_var.get()
            old_type = self.auto_include_manager.get_card_type(card)

            if new_type != old_type:
                self.auto_include_manager.set_card_type(card, new_type)
                updated_count += 1

        if updated_count > 0:
            self.log(f"Updated {updated_count} card types")
        else:
            self.log("No card types were changed")

    def toggle_card_enabled(self, card, var):
        """Toggle whether a card is enabled/disabled for auto-include"""
        color = self.auto_include_color_var.get()
        enabled = var.get()

        print(f"Toggling card '{card}' for {color} to {'enabled' if enabled else 'disabled'}")

        if self.auto_include_manager.toggle_card_enabled(color, card, enabled):
            self.log(f"{'Enabled' if enabled else 'Disabled'} {card} for {color}")
        else:
            self.log(f"Failed to {'enable' if enabled else 'disable'} {card}")
            # Reset the checkbox to its previous state
            var.set(not enabled)

    def add_auto_include(self):
        """Add a card to auto-includes for the selected color"""
        color = self.auto_include_color_var.get()
        card_name = self.card_name_var.get().strip()
        card_type = self.card_type_var.get()

        if card_name:
            if self.auto_include_manager.add_auto_include(color, card_name, card_type):
                self.update_auto_include_list()
                self.card_name_var.set("")
                self.log(f"Added {card_name} ({card_type}) to {color} auto-includes")
            else:
                self.log(f"Card {card_name} already in {color} auto-includes")

    def remove_auto_include(self):
        """Remove selected card from auto-includes"""
        color = self.auto_include_color_var.get()
        selected_cards = [card for card, var in self.checkbox_vars.items() if var.get()]

        if not selected_cards:
            self.log("No card selected for removal")
            print("No card was selected in the auto-include list")
            return

        selected_card = selected_cards[0]
        # Debug information
        print(f"Removing card: '{selected_card}' from color: '{color}'")
        print(f"Before removal, {color} has: {self.auto_include_manager.auto_includes.get(color, [])}")

        if self.auto_include_manager.remove_auto_include(color, selected_card):
            self.update_auto_include_list()
            self.log(f"Removed {selected_card} from {color} auto-includes")
            print(f"After removal, {color} has: {self.auto_include_manager.auto_includes.get(color, [])}")
        else:
            self.log(f"Failed to remove {selected_card} from {color} auto-includes")
            print(f"Removal failed. Color or card might not exist in auto_includes dictionary")

    def browse_csv_file(self):
        filename = filedialog.askopenfilename(
            initialdir=".",
            title="Select Card Collection CSV",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filename:
            self.csv_path_var.set(filename)

    def log(self, message, level="INFO"):
        """Log a message to both console and GUI"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}"

        # Always print to console
        print(log_message)

        # Update GUI if available
        if self.log_text:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            self.root.update_idletasks()

    def debug(self, message):
        """Log a debug message (only if debug mode is enabled)"""
        if self.debug_mode:
            self.log(message, level="DEBUG")

    def run_analysis(self):
        # Get input values
        csv_path = self.csv_path_var.get()
        commander_ids_str = self.commander_var.get()
        output_name = self.name_var.get()
        colors = self.get_selected_colors()
        land_count = self.land_count_var.get()
        page_limit = self.page_limit_var.get()  # Get the page limit value

        self.log("Starting analysis...")

        if not csv_path:
            self.log("Error: Please select a card collection CSV file.")
            return

        if not os.path.exists(csv_path):
            self.log(f"Error: CSV file not found at {csv_path}")
            return

        if not colors:
            self.log("Error: Please select at least one commander color.")
            return

        commander_ids = [cmd_id.strip() for cmd_id in commander_ids_str.split(",")]

        # Disable buttons during analysis
        self.run_button.config(state="disabled")

        # Set up the analyzer with the custom output name
        self.analyzer = MoxfieldAnalyzer(output_dir=f"moxfield_data_{output_name}")

        # IMPORTANT: Set the auto_include_manager to the instance we've been using in the UI
        # This ensures that any auto-includes added in the UI are used during analysis
        self.analyzer.auto_include_manager = self.auto_include_manager
        # Pass land count to the analyzer
        self.analyzer.land_count = land_count
        self.log(f"Using auto-include manager with file: {self.auto_include_manager.auto_include_file}")
        self.log(f"Target land count: {land_count}")
        self.log(f"Pages to scrape per commander: {page_limit} (up to {page_limit * 64} decks per commander)")

        # Start analysis in a separate thread
        thread = threading.Thread(
            target=self.run_analysis_thread,
            args=(csv_path, commander_ids, output_name, colors, page_limit)
        )
        thread.daemon = True
        thread.start()

    def run_analysis_thread(self, csv_path, commander_ids, output_name, colors, page_limit):
        try:
            # Debug auto-includes
            self.log(f"Selected colors: {colors}")

            # Display the auto-include management instance
            self.log(f"Auto-include manager using file: {self.analyzer.auto_include_manager.auto_include_file}")

            # Display the current auto-include lists for each relevant color
            self.log("Checking auto-include lists for selected colors:")
            for color in colors:
                cards = self.analyzer.auto_include_manager.auto_includes.get(color, [])
                self.log(f"Auto-includes for {color}: {cards}")

            # Check for GREY cards
            grey_cards = self.analyzer.auto_include_manager.auto_includes.get("GREY", [])
            if grey_cards:
                self.log(f"GREY auto-includes (should always be included): {grey_cards}")
            else:
                self.log("No GREY auto-include cards found.")

            # Check for color pair cards
            self.log("Checking two-color combinations:")
            if len(colors) >= 2:
                for i in range(len(colors)):
                    for j in range(i + 1, len(colors)):
                        color1 = colors[i]
                        color2 = colors[j]
                        # Ensure consistent ordering for the key (sort alphabetically)
                        sorted_colors = sorted([color1, color2])
                        color_pair = f"{sorted_colors[0]}_{sorted_colors[1]}"

                        pair_cards = self.analyzer.auto_include_manager.auto_includes.get(color_pair, [])
                        self.log(f"Auto-includes for pair {color_pair}: {pair_cards}")

            # Get final combined auto-includes
            auto_includes = self.analyzer.auto_include_manager.get_auto_includes(colors)
            self.log(f"Final combined auto-includes for {colors}: {auto_includes}")

            # Load owned cards
            self.log(f"Loading owned cards from {csv_path}...")
            cards_loaded = self.analyzer.load_owned_cards(csv_path)
            self.log(f"Loaded {cards_loaded} unique cards from your collection")
            self.progress_var.set(10)

            all_public_ids = []

            # Check if we already have stored IDs
            ids_file = f"{self.analyzer.output_dir}/all_public_ids.json"
            if os.path.exists(ids_file):
                with open(ids_file, "r") as f:
                    all_public_ids = json.load(f)
                self.log(f"Loaded {len(all_public_ids)} existing deck IDs")
            else:
                # Collect deck IDs for each commander
                self.log(f"Will scrape up to {page_limit} pages per commander ({page_limit * 64} decks per commander)")
                for i, commander_id in enumerate(commander_ids):
                    self.log(f"Searching for decks with commander ID: {commander_id}...")
                    public_ids = self.analyzer.search_decks_by_commander(commander_id, page_limit=page_limit)
                    all_public_ids.extend(public_ids)
                    progress = 10 + (i + 1) * 20 / len(commander_ids)
                    self.progress_var.set(progress)

                # Remove duplicates
                all_public_ids = list(set(all_public_ids))
                self.log(f"Total unique decks found: {len(all_public_ids)}")

                # Save all public IDs
                with open(ids_file, "w") as f:
                    json.dump(all_public_ids, f, indent=2)

            # Collect all decklists
            self.log("Collecting decklists (this may take a while)...")
            successful = self.analyzer.collect_decklists_parallel(
                all_public_ids,
                max_workers=5,
                progress_callback=self.update_progress
            )
            self.log(f"Successfully collected {successful} new decklists")
            self.progress_var.set(70)

            # Analyze the collected data
            self.log("Analyzing collected decklists...")
            card_frequency, synergy_matrix, cards_per_deck, deck_count = self.analyzer.analyze_all_decklists()
            self.log(f"Analysis complete! Found data for {deck_count} decks with {len(card_frequency)} unique cards")
            self.progress_var.set(85)

            # Generate reports
            self.log("Generating reports...")
            self.all_cards_df = self.analyzer.generate_owned_vs_scraped_report(card_frequency)
            self.recommended_df = self.analyzer.generate_recommended_decklist(
                card_frequency, synergy_matrix, cards_per_deck, colors=colors
            )
            self.progress_var.set(100)

            self.log(f"Generated a recommended deck with {len(self.recommended_df)} cards")
            self.log(f"Reports have been saved to the {self.analyzer.output_dir}/analysis directory")

            # Update the results view
            self.root.after(0, self.update_results_view)

            # Create visualizer and update visualization tab
            self.visualizer = SimpleCardVisualizer(output_dir=self.analyzer.output_dir)
            self.root.after(0, self.update_visualization_tab)

            # Enable export button
            self.root.after(0, lambda: self.export_button.config(state="normal"))

            # Re-enable run button
            self.root.after(0, lambda: self.run_button.config(state="normal"))

            # Switch to results tab
            self.root.after(0, lambda: self.notebook.select(1))

        except Exception as e:
            import traceback
            self.log(f"Error during analysis: {str(e)}")
            self.log(traceback.format_exc())
            self.root.after(0, lambda: self.run_button.config(state="normal"))

    def update_progress(self, value):
        # Scale value from 0-100 to 30-70 (for collection phase)
        scaled = 30 + (value * 40 / 100)
        self.progress_var.set(scaled)

    def update_results_view(self):
        # Clear existing data
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        # Check which view is selected
        view_type = self.view_type_var.get()

        if view_type == "all_cards" and hasattr(self, 'all_cards_df'):
            df = self.all_cards_df
            freq_col = 'Deck Count'

            # Add rank column for all_cards based on frequency
            df = df.sort_values(freq_col, ascending=False)
            df['Rank'] = range(1, len(df) + 1)

            # Add placeholder synergy score for all_cards view
            df['Synergy Score'] = ''

        elif view_type == "recommended" and hasattr(self, 'recommended_df'):
            df = self.recommended_df
            freq_col = 'Frequency'
        else:
            return

        # Clear any existing color frames
        if hasattr(self, 'mana_color_frames'):
            for frame in self.mana_color_frames:
                if frame and frame.winfo_exists():
                    frame.destroy()
        self.mana_color_frames = []

        # Insert data into treeview and create custom color grid
        for _, row in df.iterrows():
            is_auto_include = row.get('Auto-Include', False)
            is_owned = row.get('Owned', False)

            # Parse mana cost to check for each color
            mana_cost = row.get('Mana Cost', '')
            has_white = '{W}' in mana_cost
            has_blue = '{U}' in mana_cost
            has_black = '{B}' in mana_cost
            has_red = '{R}' in mana_cost
            has_green = '{G}' in mana_cost
            has_colors = has_white or has_blue or has_black or has_red or has_green

            # Create values array (we'll use empty text in mana columns)
            values = (
                row.get('Rank', ''),
                row.get('Card Name', ''),
                "",  # White - Empty because we'll overlay a colored frame
                "",  # Blue - Empty because we'll overlay a colored frame
                "",  # Black - Empty because we'll overlay a colored frame
                "",  # Red - Empty because we'll overlay a colored frame
                "",  # Green - Empty because we'll overlay a colored frame
                row.get(freq_col, 0),
                row.get('Card Type', 'Unknown'),
                row.get('Synergy Score', ''),
                "Yes" if is_owned else "No",
                row.get('Quantity Owned', 0),
                "Yes" if is_auto_include else "No"
            )

            # Apply appropriate tag for row highlighting
            if is_auto_include:
                tag = 'auto_include'  # Yellow highlighting for auto-includes
            elif is_owned:
                tag = 'owned'  # Blue highlighting for owned cards
            else:
                tag = ''  # No highlighting for other cards

            tags = (tag,) if tag else ()

            # Insert the row with appropriate tags
            item_id = self.results_tree.insert('', 'end', values=values, tags=tags)

            # Store mana color information for this row
            # This will be used by the mana_color_grid.create_color_cells function
            self.mana_colors_data.append({
                'item_id': item_id,
                'W': has_white,
                'U': has_blue,
                'B': has_black,
                'R': has_red,
                'G': has_green,
                'colorless': not has_colors and mana_cost
            })

        # Reapply the sort if there was one
        if hasattr(self, 'sort_column'):
            self.sort_treeview(self.sort_column, numeric=(self.sort_column in ["Rank", "Frequency", "Quantity"]))

        # Update the mana color grid after a short delay to ensure tree is fully rendered
        self.root.after(100, self.mana_color_grid.create_color_cells)

    def setup_results_tab(self):
        # Configure grid weights for resizing
        self.results_tab.rowconfigure(0, weight=0)  # Control frame - fixed size
        self.results_tab.rowconfigure(1, weight=1)  # Results frame - expands to fill space
        self.results_tab.columnconfigure(0, weight=1)  # Both frames expand horizontally

        # Results control frame
        control_frame = tk.Frame(self.results_tab, bg="#f0f0f0")
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        # View type selector
        view_label = tk.Label(control_frame, text="View:", bg="#f0f0f0")
        view_label.pack(side="left", padx=5)

        self.view_type_var = tk.StringVar(value="recommended")
        view_types = [
            ("Recommended Deck", "recommended"),
            ("All Cards", "all_cards"),
        ]

        for text, value in view_types:
            rb = tk.Radiobutton(
                control_frame,
                text=text,
                variable=self.view_type_var,
                value=value,
                bg="#f0f0f0",
                command=self.update_results_view
            )
            rb.pack(side="left", padx=5)

        # Export button
        self.export_button = tk.Button(
            control_frame,
            text="Export to CSV",
            command=self.export_current_view,
            bg="#e0e0e0",
            state="disabled"
        )
        self.export_button.pack(side="right", padx=10)

        # Filter label (placeholder for future feature)
        filter_label = tk.Label(control_frame, text="Filters coming soon...", bg="#f0f0f0", fg="#888888")
        filter_label.pack(side="right", padx=10)

        # Results frame (will contain treeview)
        results_frame = tk.Frame(self.results_tab, bg="#f0f0f0")
        results_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Configure results frame to resize properly
        results_frame.rowconfigure(0, weight=0)  # Color legend - fixed height
        results_frame.rowconfigure(1, weight=1)  # Tree container - expands
        results_frame.columnconfigure(0, weight=1)  # Expand horizontally

        # Color legend for mana symbols
        legend_frame = tk.Frame(results_frame, bg="#f0f0f0")
        legend_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Mana symbol legend
        # White Mana
        white_frame = tk.Frame(legend_frame, bg="white", width=25, height=25)
        white_frame.pack(side="left", padx=2)
        tk.Label(white_frame, text="W", bg="white").pack(fill="both", expand=True)

        # Blue Mana
        blue_frame = tk.Frame(legend_frame, bg="blue", width=25, height=25)
        blue_frame.pack(side="left", padx=2)
        tk.Label(blue_frame, text="U", bg="blue", fg="white").pack(fill="both", expand=True)

        # Black Mana
        black_frame = tk.Frame(legend_frame, bg="black", width=25, height=25)
        black_frame.pack(side="left", padx=2)
        tk.Label(black_frame, text="B", bg="black", fg="white").pack(fill="both", expand=True)

        # Red Mana
        red_frame = tk.Frame(legend_frame, bg="red", width=25, height=25)
        red_frame.pack(side="left", padx=2)
        tk.Label(red_frame, text="R", bg="red", fg="white").pack(fill="both", expand=True)

        # Green Mana
        green_frame = tk.Frame(legend_frame, bg="green", width=25, height=25)
        green_frame.pack(side="left", padx=2)
        tk.Label(green_frame, text="G", bg="green", fg="white").pack(fill="both", expand=True)

        # We need a container frame for the treeview and color overlays
        tree_container = tk.Frame(results_frame, bg="#f0f0f0")
        tree_container.grid(row=1, column=0, sticky="nsew")

        # Configure tree container for proper resizing
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        # Set up treeview for results
        self.results_tree = ttk.Treeview(tree_container)
        self.results_tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbars to the treeview
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.results_tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.results_tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")

        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.results_tree["columns"] = (
            "Rank", "Card Name", "W", "U", "B", "R", "G", "Frequency", "Card Type", "Synergy Score", "Owned",
            "Quantity",
            "Auto-Include")

        self.results_tree.column("#0", width=0, stretch=tk.NO)
        self.results_tree.column("Rank", width=50, anchor=tk.CENTER)
        self.results_tree.column("Card Name", width=200, anchor=tk.W)

        # Mana color columns - small width, centered
        self.results_tree.column("W", width=25, anchor=tk.CENTER)
        self.results_tree.column("U", width=25, anchor=tk.CENTER)
        self.results_tree.column("B", width=25, anchor=tk.CENTER)
        self.results_tree.column("R", width=25, anchor=tk.CENTER)
        self.results_tree.column("G", width=25, anchor=tk.CENTER)

        self.results_tree.column("Frequency", width=80, anchor=tk.CENTER)
        self.results_tree.column("Card Type", width=100, anchor=tk.CENTER)
        self.results_tree.column("Synergy Score", width=100, anchor=tk.CENTER)
        self.results_tree.column("Owned", width=70, anchor=tk.CENTER)
        self.results_tree.column("Quantity", width=70, anchor=tk.CENTER)
        self.results_tree.column("Auto-Include", width=90, anchor=tk.CENTER)

        self.results_tree.heading("#0", text="")
        self.results_tree.heading("Rank", text="Rank", command=lambda: self.sort_treeview("Rank", numeric=True))
        self.results_tree.heading("Card Name", text="Card Name", command=lambda: self.sort_treeview("Card Name"))

        # Hide the mana color heading text since we have the colored labels above
        self.results_tree.heading("W", text="")
        self.results_tree.heading("U", text="")
        self.results_tree.heading("B", text="")
        self.results_tree.heading("R", text="")
        self.results_tree.heading("G", text="")

        self.results_tree.heading("Frequency", text="Frequency",
                                  command=lambda: self.sort_treeview("Frequency", numeric=True))
        self.results_tree.heading("Card Type", text="Card Type", command=lambda: self.sort_treeview("Card Type"))
        self.results_tree.heading("Synergy Score", text="Synergy Score",
                                  command=lambda: self.sort_treeview("Synergy Score", numeric=True))
        self.results_tree.heading("Owned", text="Owned", command=lambda: self.sort_treeview("Owned"))
        self.results_tree.heading("Quantity", text="Quantity",
                                  command=lambda: self.sort_treeview("Quantity", numeric=True))
        self.results_tree.heading("Auto-Include", text="Auto-Include",
                                  command=lambda: self.sort_treeview("Auto-Include"))

        # List for storing color frames created for the mana symbols
        self.mana_color_frames = []

        # Initialize our mana color data storage
        self.mana_colors_data = []

        # Create a special utility class to handle the colored cells
        class ManaColorGrid:
            def __init__(self, tree, parent_app):
                self.tree = tree
                self.parent = parent_app

            def create_color_cells(self):
                """Create colored cells for the mana symbols"""
                # Clear any existing frames
                for frame in self.parent.mana_color_frames:
                    if frame and frame.winfo_exists():
                        frame.destroy()
                self.parent.mana_color_frames = []

                # For each row with color data
                for color_data in self.parent.mana_colors_data:
                    item_id = color_data['item_id']

                    # Only process if the item still exists
                    if not self.tree.exists(item_id):
                        continue

                    # Get the item's location - we need this to position our color cells
                    item_id_bbox = self.tree.bbox(item_id)
                    if not item_id_bbox:
                        continue  # Skip if not visible

                    # Create frames for each mana color
                    mana_columns = ["W", "U", "B", "R", "G"]
                    for i, col in enumerate(mana_columns):
                        # Only create color for columns that have mana or are colorless
                        if color_data.get(col, False) or color_data.get('colorless', False):
                            # Get the column's position
                            col_id = i + 2  # Offset for Rank, Card Name
                            col_bbox = self.tree.bbox(item_id, col_id)

                            if col_bbox:
                                x, y, width, height = col_bbox

                                # Determine the color
                                if color_data.get('colorless', False):
                                    bg_color = 'gray'
                                elif col == "W":
                                    bg_color = 'white'
                                elif col == "U":
                                    bg_color = 'blue'
                                elif col == "B":
                                    bg_color = 'black'
                                elif col == "R":
                                    bg_color = 'red'
                                elif col == "G":
                                    bg_color = 'green'

                                # Create a colored frame at this position
                                color_frame = tk.Frame(
                                    self.tree,
                                    bg=bg_color,
                                    borderwidth=0,
                                    height=height - 1,
                                    width=width - 1
                                )
                                color_frame.place(x=x, y=y)

                                # Store the frame for later cleanup
                                self.parent.mana_color_frames.append(color_frame)

        # Initialize the color grid
        self.mana_color_grid = ManaColorGrid(self.results_tree, self)

        # Bind events to refresh the color grid on changes
        self.results_tree.bind("<Motion>", lambda e: self.root.after(100, self.mana_color_grid.create_color_cells))
        self.results_tree.bind("<<TreeviewSelect>>",
                               lambda e: self.root.after(100, self.mana_color_grid.create_color_cells))
        self.results_tree.bind("<Configure>", lambda e: self.root.after(100, self.mana_color_grid.create_color_cells))

        # Add tags for highlighting different types of cards
        self.results_tree.tag_configure('auto_include', background='#ffff99')  # Light yellow for auto-includes
        self.results_tree.tag_configure('owned', background='#add8e6')  # Light blue for owned cards

    def update_visualization_tab(self):
        # Remove placeholder
        if self.vis_placeholder.winfo_manager():
            self.vis_placeholder.grid_forget()

        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Add text summary if visualizer is available
        if self.visualizer:
            summary_text = self.visualizer.create_text_summary(self.chart_frame)
            if summary_text:
                summary_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            else:
                # Re-add placeholder if visualizer failed
                self.vis_placeholder.grid(row=0, column=0, sticky="nsew", pady=50)
        else:
            # Re-add placeholder if visualizer failed
            self.vis_placeholder.grid(row=0, column=0, sticky="nsew", pady=50)

    def export_current_view(self):
        view_type = self.view_type_var.get()

        if view_type == "all_cards" and hasattr(self, 'all_cards_df'):
            df = self.all_cards_df
            default_filename = "all_cards_analysis.csv"
        elif view_type == "recommended" and hasattr(self, 'recommended_df'):
            df = self.recommended_df
            default_filename = "recommended_decklist.csv"
        else:
            return

        # Ask for save location
        filename = filedialog.asksaveasfilename(
            initialdir=".",
            title="Save CSV File",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )

        if filename:
            df.to_csv(filename, index=False)
            self.log(f"Exported to {filename}")

    def highlight_mana_cells(self, event=None):
        """Apply color highlighting to mana symbol cells after rendering"""
        # Since ttk.Treeview doesn't support cell-level styling directly,
        # we'll handle this with custom rendering using Canvas

        # This method will be used as a fallback to the style-based approach
        # If we find the style-based approach doesn't work consistently, we can
        # enhance this method to manually draw colored cells

        # Using ttk styles with a custom Canvas approach would be the most reliable
        # but it's complex to implement and beyond the scope of a quick fix
        pass

    def setup_visualization_tab(self):
        # Configure grid for resizing
        self.visualization_tab.rowconfigure(0, weight=1)
        self.visualization_tab.columnconfigure(0, weight=1)

        # Frame for charts
        self.chart_frame = tk.Frame(self.visualization_tab, bg="#f0f0f0")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Configure chart frame for resizing
        self.chart_frame.rowconfigure(0, weight=1)
        self.chart_frame.columnconfigure(0, weight=1)

        # Add a label explaining that visualizations will appear after analysis
        self.vis_placeholder = tk.Label(
            self.chart_frame,
            text="Visualizations will appear here after running the analysis.",
            font=Font(family="Helvetica", size=12),
            bg="#f0f0f0",
            fg="#555555"
        )
        self.vis_placeholder.grid(row=0, column=0, sticky="nsew", pady=50)

    def sort_treeview(self, column, numeric=False):
        """Sort treeview when column heading is clicked"""
        # If same column, flip the sort direction
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            # New column, default to ascending
            self.sort_ascending = True
            self.sort_column = column

        # Get all items from treeview
        items = [(self.results_tree.set(item, column), item) for item in self.results_tree.get_children('')]

        # Sort based on numeric or string comparison
        if numeric:
            # Handle empty values properly for numeric sorting
            def safe_float(val):
                try:
                    return float(val) if val else 0
                except ValueError:
                    return 0

            items.sort(key=lambda x: safe_float(x[0]), reverse=not self.sort_ascending)
        else:
            items.sort(key=lambda x: x[0].lower(), reverse=not self.sort_ascending)

        # Rearrange items in the sorted order
        for index, (val, item) in enumerate(items):
            self.results_tree.move(item, '', index)

        # Update column headings to show sort direction
        for col in self.results_tree["columns"]:
            if col == column:
                direction = "▲" if self.sort_ascending else "▼"
                self.results_tree.heading(col, text=f"{col} {direction}")
            else:
                # Remove sort indicator from other columns
                self.results_tree.heading(col, text=col)


class MoxfieldAnalyzer:
    def __init__(self, output_dir="moxfield_data"):
        """Initialize the analyzer with a scraper and output directory."""
        self.scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        })
        self.output_dir = output_dir
        self.owned_cards = set()
        self.card_quantities = {}
        self.auto_include_manager = AutoIncludeManager(output_dir)
        self.card_types = {}  # Dictionary to store card types
        self.card_mana_costs = {}  # Dictionary to store mana costs
        self.land_count = 37  # Default land count if not specified

        # Basic lands that can be included multiple times
        self.basic_lands = ["forest", "swamp", "mountain", "plains", "island"]

        # Create output directories if they don't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(f"{output_dir}/decklists"):
            os.makedirs(f"{output_dir}/decklists")
        if not os.path.exists(f"{output_dir}/analysis"):
            os.makedirs(f"{output_dir}/analysis")

        # For tracking progress
        self.collected_decks = set()
        if os.path.exists(f"{output_dir}/collected_decks.json"):
            with open(f"{output_dir}/collected_decks.json", "r") as f:
                self.collected_decks = set(json.load(f))

    def load_owned_cards(self, csv_file):
        """
        Load owned cards from a CSV file.

        Args:
            csv_file (str): Path to the CSV file with owned cards

        Returns:
            int: Number of owned cards loaded
        """
        try:
            # Check for the "sep=" line in the CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('"sep='):
                    delimiter = first_line.split('=')[1].strip('"')
                else:
                    delimiter = ','  # Default delimiter

            # Read the CSV file
            df = pd.read_csv(csv_file, delimiter=delimiter, skiprows=1 if first_line.startswith('"sep=') else 0)

            # Get card names and quantities
            if 'Card Name' in df.columns and 'Quantity' in df.columns:
                for _, row in df.iterrows():
                    card_name = row['Card Name']
                    quantity = row['Quantity']

                    # Normalize card name (remove special characters, lowercase)
                    normalized_name = self.normalize_card_name(card_name)

                    self.owned_cards.add(normalized_name)
                    self.card_quantities[normalized_name] = quantity

            print(f"Loaded {len(self.owned_cards)} unique cards from your collection")
            return len(self.owned_cards)

        except Exception as e:
            print(f"Error loading owned cards: {str(e)}")
            return 0

    def normalize_card_name(self, card_name):
        """Normalize card name to handle variations in naming."""
        # Convert to lowercase
        normalized = str(card_name).lower()

        # Remove special characters, but keep spaces
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def save_collection_progress(self):
        """Save the list of collected decks to avoid re-downloading."""
        with open(f"{self.output_dir}/collected_decks.json", "w") as f:
            json.dump(list(self.collected_decks), f)

    def search_decks_by_commander(self, commander_id, page_limit=10):
        """
        Search for decks using a specific commander.

        Args:
            commander_id (str): The Moxfield card ID for the commander
            page_limit (int): Maximum number of pages to retrieve (each page contains 64 decks,
                             so page_limit=10 means up to 640 decks could be scraped)

        Returns:
            list: List of deck public IDs for the commander
        """
        all_public_ids = []
        page_number = 1

        print(f"Searching for decks with commander ID: {commander_id}")
        print(f"Will scrape up to {page_limit} pages (max {page_limit * 64} decks)")

        while page_number <= page_limit:
            url = f"https://api2.moxfield.com/v2/decks/search-sfw?pageNumber={page_number}&pageSize=64&sortType=likes&sortDirection=descending&commanderCardId={commander_id}"
            try:
                response = self.scraper.get(url)
                if response.status_code != 200:
                    print(f"Error on page {page_number}: {response.status_code}")
                    break

                data = response.json()

                # Check if we've reached the end of results
                if len(data.get('data', [])) == 0:
                    print(f"No more decks found after page {page_number - 1}")
                    break

                # Extract public IDs
                public_ids = [deck['publicId'] for deck in data.get('data', [])]
                all_public_ids.extend(public_ids)

                print(f"Found {len(public_ids)} decks on page {page_number}")

                # Save progress after each page
                page_number += 1

                # Add a small delay to avoid rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"Error fetching page {page_number}: {str(e)}")
                break

        print(f"Total decks found for commander {commander_id}: {len(all_public_ids)}")
        return all_public_ids

    def get_decklist(self, public_id):
        """
        Retrieve a complete decklist by its public ID.

        Args:
            public_id (str): The public ID of the deck

        Returns:
            dict: The full deck data or None if unsuccessful
        """
        # Skip if already collected
        if public_id in self.collected_decks:
            return None

        url = f"https://api2.moxfield.com/v2/decks/all/{public_id}"
        try:
            response = self.scraper.get(url)
            if response.status_code != 200:
                print(f"Error fetching deck {public_id}: {response.status_code}")
                return None

            data = response.json()

            # Save the decklist to file
            output_path = f"{self.output_dir}/decklists/{public_id}.json"
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            # Mark as collected
            self.collected_decks.add(public_id)

            # Return the data for further processing if needed
            return data

        except Exception as e:
            print(f"Error fetching deck {public_id}: {str(e)}")
            return None

    def collect_decklists_parallel(self, public_ids, max_workers=5, progress_callback=None):
        """
        Collect decklists in parallel using ThreadPoolExecutor.

        Args:
            public_ids (list): List of public IDs to collect
            max_workers (int): Maximum number of parallel workers
            progress_callback (function): Callback for progress updates

        Returns:
            int: Number of successfully collected decklists
        """
        # Filter out already collected decks
        new_ids = [pid for pid in public_ids if pid not in self.collected_decks]
        print(f"Collecting {len(new_ids)} new decklists (skipping {len(public_ids) - len(new_ids)} already collected)")

        successful = 0
        total = len(new_ids)
        completed = 0

        # Function to update progress after each download
        def update_progress(future):
            nonlocal completed
            completed += 1
            if progress_callback:
                progress_callback(100 * completed / total)

        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for pid in new_ids:
                future = executor.submit(self.get_decklist, pid)
                future.add_done_callback(update_progress)
                futures.append(future)

            # Wait for all futures to complete
            for future in futures:
                result = future.result()
                if result is not None:
                    successful += 1

        # Save collection progress
        self.save_collection_progress()

        return successful

    def analyze_all_decklists(self):
        """
        Analyze all collected decklists to generate statistics and card correlations.

        Returns:
            tuple: (card_frequency, synergy_matrix, cards_per_deck, deck_count)
        """
        print("Analyzing collected decklists...")

        card_frequency = Counter()
        deck_count = 0
        synergy_pairs = Counter()
        cards_per_deck = []

        # Iterate through all collected decklist files
        for filename in os.listdir(f"{self.output_dir}/decklists"):
            if filename.endswith('.json'):
                deck_path = f"{self.output_dir}/decklists/{filename}"
                with open(deck_path, 'r') as f:
                    try:
                        deck_data = json.load(f)
                        deck_count += 1

                        # Get all cards in this deck (excluding basic lands)
                        deck_cards = set()

                        for card_id, card_info in deck_data.get('mainboard', {}).items():
                            card_name = card_info.get('card', {}).get('name', '')
                            card_type_line = card_info.get('card', {}).get('type_line', '')
                            mana_cost = card_info.get('card', {}).get('mana_cost', '')

                            # Skip basic lands
                            if 'Basic Land' in card_type_line:
                                continue

                            if card_name:
                                normalized_name = self.normalize_card_name(card_name)
                                deck_cards.add(normalized_name)
                                card_frequency[normalized_name] += 1

                                # Store card type if not already stored or if current type is more specific
                                if normalized_name not in self.card_types:
                                    self.card_types[normalized_name] = self.get_card_type(card_type_line)

                                # Store mana cost if available
                                if mana_cost and not hasattr(self, 'card_mana_costs'):
                                    self.card_mana_costs = {}
                                if mana_cost:
                                    self.card_mana_costs[normalized_name] = mana_cost

                        # Add all commanders
                        for card_id, card_info in deck_data.get('commanders', {}).items():
                            card_name = card_info.get('card', {}).get('name', '')
                            card_type_line = card_info.get('card', {}).get('type_line', '')
                            mana_cost = card_info.get('card', {}).get('mana_cost', '')

                            if card_name:
                                normalized_name = self.normalize_card_name(card_name)
                                deck_cards.add(normalized_name)
                                card_frequency[normalized_name] += 1

                                # Store card type for commanders too
                                if normalized_name not in self.card_types:
                                    self.card_types[normalized_name] = self.get_card_type(card_type_line)

                                # Store mana cost for commanders too
                                if mana_cost and not hasattr(self, 'card_mana_costs'):
                                    self.card_mana_costs = {}
                                if mana_cost:
                                    self.card_mana_costs[normalized_name] = mana_cost

                        # Record this deck's cards
                        cards_per_deck.append(deck_cards)

                        # Calculate card synergies (which cards appear together)
                        deck_cards_list = list(deck_cards)
                        for i in range(len(deck_cards_list)):
                            for j in range(i + 1, len(deck_cards_list)):
                                card_pair = tuple(sorted([deck_cards_list[i], deck_cards_list[j]]))
                                synergy_pairs[card_pair] += 1

                    except json.JSONDecodeError:
                        print(f"Error parsing {filename}")

        print(f"Analyzed {deck_count} decks with {len(card_frequency)} unique cards")

        # Calculate normalized synergy scores
        synergy_matrix = defaultdict(dict)

        for (card1, card2), count in synergy_pairs.items():
            # Calculate Jaccard index as synergy score
            # (how often these cards appear together relative to how often they appear at all)
            both = count
            total = card_frequency[card1] + card_frequency[card2] - both

            if total > 0:
                synergy_score = both / total

                # Only keep scores above a threshold
                if synergy_score > 0.1:  # Adjust threshold as needed
                    synergy_matrix[card1][card2] = synergy_score
                    synergy_matrix[card2][card1] = synergy_score

        return card_frequency, synergy_matrix, cards_per_deck, deck_count

    def generate_owned_vs_scraped_report(self, card_frequency):
        """
        Generate a report of owned cards vs. scraped cards.

        Args:
            card_frequency (Counter): Frequency of cards in scraped decks

        Returns:
            DataFrame: Report data
        """
        # Create a dataframe with all cards from scraped decks
        scraped_cards = []

        for card, frequency in card_frequency.items():
            # Ensure the card_mana_costs dictionary exists
            if not hasattr(self, 'card_mana_costs'):
                self.card_mana_costs = {}

            scraped_cards.append({
                'Card Name': card,
                'Mana Cost': self.card_mana_costs.get(card, ''),
                'Deck Count': frequency,
                'Card Type': self.card_types.get(card, "Unknown"),
                'Owned': card in self.owned_cards,
                'Quantity Owned': self.card_quantities.get(card, 0) if card in self.owned_cards else 0
            })

        # Create DataFrame and sort by frequency
        df = pd.DataFrame(scraped_cards)
        df = df.sort_values('Deck Count', ascending=False)

        # Export to CSV
        output_path = f"{self.output_dir}/analysis/all_cards_analysis.csv"
        df.to_csv(output_path, index=False)

        print(f"Exported all cards analysis to {output_path}")
        return df

    def generate_recommended_decklist(self, card_frequency, synergy_matrix, cards_per_deck, target_size=100,
                                      colors=None):
        """
        Generate a recommended decklist based on owned cards and card synergies.

        Args:
            card_frequency (Counter): Frequency of cards in scraped decks
            synergy_matrix (dict): Card synergy matrix
            cards_per_deck (list): List of sets, where each set contains the cards in a deck
            target_size (int): Target size of the recommended deck
            colors (list): List of commander colors

        Returns:
            DataFrame: Recommended decklist
        """
        print(f"Generating recommended decklist with target land count: {self.land_count}")

        # Calculate non-land count based on target size and land count
        non_land_count = target_size - self.land_count
        print(f"Target breakdown: {self.land_count} lands + {non_land_count} non-lands = {target_size} total cards")

        # Track lands and non-lands separately
        lands = []
        non_lands = []

        # Start with auto-include cards if colors are specified
        recommended = []
        auto_includes = []
        if colors:
            auto_includes = self.auto_include_manager.get_auto_includes(colors)
            recommended.extend(auto_includes)
            print(f"Added {len(auto_includes)} auto-include cards for colors: {colors}")
            print("Auto-includes:", auto_includes)  # Debug print

        # Add cards we own that appear frequently in scraped decks
        owned_in_scraped = [(card, freq) for card, freq in card_frequency.items() if card in self.owned_cards]
        owned_in_scraped.sort(key=lambda x: x[1], reverse=True)

        # Seed our recommended deck with the most popular owned cards
        seed_count = min(10, len(owned_in_scraped))
        seed_cards = [card for card, _ in owned_in_scraped[:seed_count]]
        for card in seed_cards:
            if card not in recommended:
                recommended.append(card)

        # Find the most synergistic cards to add to our seed cards
        # But leave room for all auto-includes
        remaining_slots = target_size - len(auto_includes)

        # Calculate a score for each candidate card
        candidate_scores = Counter()

        # First, consider synergy with our seed cards
        for card in recommended:
            if card in synergy_matrix:
                for related_card, synergy_score in synergy_matrix[card].items():
                    if related_card not in recommended:
                        candidate_scores[related_card] += synergy_score * 10  # Weight by synergy

        # Next, add frequency as a factor (popularity)
        for card, freq in card_frequency.items():
            if card not in recommended:
                # Normalize frequency score
                normalized_freq = freq / max(card_frequency.values()) if card_frequency else 0
                candidate_scores[card] += normalized_freq

                # Bonus for owned cards
                if card in self.owned_cards:
                    candidate_scores[card] *= 1.5  # 50% bonus for owned cards

        # Add commonly co-occurring cards
        # Find decks that contain at least 3 of our seed cards
        matching_decks = []
        for deck_cards in cards_per_deck:
            seed_overlap = len(set(recommended) & deck_cards)
            if seed_overlap >= 3:
                matching_decks.append(deck_cards)

        # Count cards in these matching decks
        matching_cards = Counter()
        for deck in matching_decks:
            for card in deck:
                if card not in recommended:
                    matching_cards[card] += 1

        # Add to our candidate scores
        for card, count in matching_cards.items():
            candidate_scores[card] += count / len(matching_decks) * 5 if matching_decks else 0

        # Select the top scoring cards to complete our deck
        # Note: Only fill remaining slots after accounting for auto-includes
        non_auto_includes = [card for card in recommended if card not in auto_includes]
        remaining_slots = target_size - len(auto_includes) - len(non_auto_includes)

        if remaining_slots > 0:
            top_candidates = [card for card, _ in candidate_scores.most_common(remaining_slots)]
            recommended.extend(top_candidates)

        # FIXED: Ensure auto-includes are ALWAYS in the recommended deck
        # First, remove any duplicates
        recommended = list(dict.fromkeys(recommended))

        # Then ensure auto-includes are in the list, even if it exceeds target_size
        for card in auto_includes:
            if card not in recommended:
                recommended.append(card)

        # Create a normalized map for matching auto-includes to scraped cards
        # This fixes the "sol ring" vs "Sol Ring" case sensitivity issue
        normalized_auto_includes = {self.normalize_card_name(card): card for card in auto_includes}
        normalized_card_freq = {}

        # Create a normalized map of card_frequency for matching
        for card, freq in card_frequency.items():
            normalized_card = self.normalize_card_name(card)
            if normalized_card in normalized_card_freq:
                # If two cards normalize to the same name, keep the one with higher frequency
                if freq > normalized_card_freq[normalized_card][1]:
                    normalized_card_freq[normalized_card] = (card, freq)
            else:
                normalized_card_freq[normalized_card] = (card, freq)

        # Print debug info about potential duplicates
        print("\n--- Checking for potential duplicate cards ---")
        for auto_card in auto_includes:
            norm_auto = self.normalize_card_name(auto_card)
            if norm_auto in normalized_card_freq:
                scraped_card, freq = normalized_card_freq[norm_auto]
                print(
                    f"Found potential duplicate: Auto-include '{auto_card}' matches scraped '{scraped_card}' with freq {freq}")
        print("--- End duplicate check ---\n")

        # Calculate synergy scores for each card in the recommended deck
        synergy_scores = {}
        for i, card1 in enumerate(recommended):
            synergy_scores[card1] = 0
            card_count = 0

            # Check synergy with all other cards in the deck
            for card2 in recommended:
                if card1 != card2:
                    # Get synergy score if available, otherwise 0
                    if card1 in synergy_matrix and card2 in synergy_matrix[card1]:
                        synergy_scores[card1] += synergy_matrix[card1][card2]
                        card_count += 1

            # Average the synergy score
            if card_count > 0:
                synergy_scores[card1] /= card_count

            # Debug print
            print(f"Synergy score for {card1}: {synergy_scores[card1]:.3f}")

        # Separate cards into lands and non-lands
        for card in recommended:
            is_auto_include = card in auto_includes

            # Check if this is a land
            if is_auto_include:
                card_type = self.auto_include_manager.get_card_type(card)
            else:
                card_type = self.card_types.get(card, "Unknown")

            if card_type == "Land":
                # Only include lands that are in auto-includes or that meet our criteria:
                # 1. Must be owned by the user
                # 2. Must appear in at least 30 decks
                if is_auto_include or (card in self.owned_cards and card_frequency.get(card, 0) >= 30):
                    lands.append(card)
            else:
                non_lands.append(card)

        print(f"Initial split: {len(lands)} lands, {len(non_lands)} non-lands")

        # Adjust land count to match target
        if len(lands) > self.land_count:
            # Too many lands, sort by synergy score and remove the worst
            # Prioritize auto-includes first
            lands.sort(key=lambda x: (x in auto_includes, synergy_scores.get(x, 0)), reverse=True)
            lands = lands[:self.land_count]
            print(f"Trimmed down to {len(lands)} lands")
        elif len(lands) < self.land_count:
            # Track basic lands separately, since they can be included multiple times
            basic_lands_found = []
            non_basic_lands = []

            # First, separate existing lands into basic and non-basic
            for land in lands:
                normalized_land = self.normalize_card_name(land)
                if any(basic in normalized_land for basic in self.basic_lands):
                    basic_lands_found.append(land)
                else:
                    non_basic_lands.append(land)

            print(f"Basic lands already in deck: {len(basic_lands_found)}")
            print(f"Non-basic lands in deck: {len(non_basic_lands)}")

            # Calculate how many more lands we need
            needed_lands = self.land_count - len(lands)
            print(f"Need {needed_lands} more lands to reach target {self.land_count}")

            # Look for non-basic lands that aren't already in the deck
            potential_non_basic_lands = []
            for card, freq in card_frequency.items():
                if card not in lands and card not in non_lands:
                    # Only include lands that meet our criteria:
                    # 1. Must be owned by the user
                    # 2. Must appear in at least 30 decks
                    if card in self.owned_cards and freq >= 30:
                        card_type = self.card_types.get(card, "Unknown")
                        normalized_card = self.normalize_card_name(card)

                        # Check if it's a land but not a basic land
                        if card_type == "Land" and not any(basic in normalized_card for basic in self.basic_lands):
                            potential_non_basic_lands.append((card, freq, card in self.owned_cards))

            # Sort non-basic lands: by frequency since all are owned
            potential_non_basic_lands.sort(key=lambda x: -x[1])
            print(f"Found {len(potential_non_basic_lands)} potential non-basic lands meeting criteria")

            # Add as many non-basic lands as we can, up to what we need
            if potential_non_basic_lands:
                non_basic_to_add = min(needed_lands, len(potential_non_basic_lands))
                non_basic_lands.extend([card for card, _, _ in potential_non_basic_lands[:non_basic_to_add]])
                print(f"Added {non_basic_to_add} additional non-basic lands")

            # Update needed_lands
            needed_lands -= min(needed_lands, len(potential_non_basic_lands))

            # If we still need more lands, find basic lands
            if needed_lands > 0:
                print(f"Still need {needed_lands} more lands, filling with basic lands")

                # Check what basic lands match our colors
                color_to_basic = {
                    "WHITE": "plains",
                    "BLUE": "island",
                    "BLACK": "swamp",
                    "RED": "mountain",
                    "GREEN": "forest"
                }

                # Determine which basic lands to use based on commander colors
                basic_lands_to_use = []
                if colors:
                    # Use specific basic lands matching our colors
                    for color in colors:
                        if color in color_to_basic:
                            basic_lands_to_use.append(color_to_basic[color])
                else:
                    # If no colors specified, use all basic lands
                    basic_lands_to_use = self.basic_lands

                print(f"Will use basic lands: {basic_lands_to_use}")

                # Look for basic lands in the card frequency data that we own
                basic_lands_options = []
                for card, freq in card_frequency.items():
                    if card in self.owned_cards:
                        normalized_card = self.normalize_card_name(card)
                        if any(basic in normalized_card for basic in basic_lands_to_use):
                            basic_lands_options.append((card, freq))

                if basic_lands_options:
                    # Sort by frequency
                    basic_lands_options.sort(key=lambda x: -x[1])

                    # If we have options, pick the most frequent basic land
                    best_basic_land = basic_lands_options[0][0]
                    print(f"Selected basic land to duplicate: {best_basic_land}")

                    # Add copies of the basic land as needed
                    basic_lands_found.extend([best_basic_land] * needed_lands)
                    print(f"Added {needed_lands} copies of {best_basic_land}")
                else:
                    # If no basic lands found in frequency data, use a default basic land
                    default_basic = basic_lands_to_use[0] if basic_lands_to_use else "forest"
                    print(f"No basic lands found in data, defaulting to {default_basic}")

                    # Create a capitalized version of the basic land
                    capitalized_basic = default_basic.capitalize()
                    basic_lands_found.extend([capitalized_basic] * needed_lands)
                    print(f"Added {needed_lands} copies of {capitalized_basic}")

            # Update lands list with all the basic and non-basic lands
            lands = basic_lands_found + non_basic_lands

        # Adjust the non-land count to match our target (target_size - land_count)
        if len(non_lands) > non_land_count:
            # Too many non-lands, need to trim
            # Sort by priority: auto-include, owned, synergy score
            non_lands.sort(key=lambda x: (x in auto_includes, x in self.owned_cards, synergy_scores.get(x, 0)),
                           reverse=True)
            # Keep only the top cards, but ensure all auto-includes are kept
            auto_includes_non_lands = [card for card in non_lands if card in auto_includes]
            other_non_lands = [card for card in non_lands if card not in auto_includes]

            # Keep all auto-includes but limit other non-lands
            remaining_slots = non_land_count - len(auto_includes_non_lands)
            if remaining_slots > 0:
                non_lands = auto_includes_non_lands + other_non_lands[:remaining_slots]
            else:
                # This is a rare case where we have more auto-include non-lands than our target
                # Keep all auto-includes but warn the user
                non_lands = auto_includes_non_lands
                print(
                    f"WARNING: Had to keep {len(auto_includes_non_lands)} auto-include non-lands, exceeding target of {non_land_count}")

            print(f"Trimmed non-lands from {len(non_lands)} to {non_land_count}")

        # Update the recommended deck with our adjusted land and non-land counts
        recommended = lands + non_lands
        print(f"Final deck composition: {len(lands)} lands, {len(non_lands)} non-lands, {len(recommended)} total")

        # Verify we're not exceeding the target deck size
        if len(recommended) > target_size:
            print(f"WARNING: Final deck size {len(recommended)} exceeds target {target_size}")
            # This should not happen with our adjustments, but just in case

        # Create a dataframe for the recommended deck
        deck_data = []
        processed_normalized_names = set()  # Track cards we've already processed

        # Order the recommended deck:
        # 1. Group by card type
        # 2. Within each type, order by auto-includes first, then owned cards, then others
        # 3. Within those groups, sort by synergy score

        # Define card type order for better organization
        type_order = {"Land": 1, "Creature": 2, "Artifact": 3, "Enchantment": 4, "Instant": 5, "Sorcery": 6,
                      "Unknown": 7}

        # Create groups based on type
        card_by_type = defaultdict(list)

        for card in recommended:
            is_auto_include = card in auto_includes
            is_owned = card in self.owned_cards

            # Determine card type
            if is_auto_include:
                card_type = self.auto_include_manager.get_card_type(card)
            else:
                card_type = self.card_types.get(card, "Unknown")

            # If this is a basic land but card type is Unknown, set to Land
            if card_type == "Unknown" and self.is_basic_land(card):
                card_type = "Land"

            # Add to appropriate group
            card_by_type[card_type].append((card, is_auto_include, is_owned, synergy_scores.get(card, 0)))

        # Sort each type group by auto-include, owned, then synergy score
        for card_type in card_by_type:
            card_by_type[card_type].sort(key=lambda x: (not x[1], not x[2], -x[3]))

        # Flatten the ordered list, putting types in our defined order
        ordered_recommended = []
        for card_type in sorted(card_by_type.keys(), key=lambda x: type_order.get(x, 999)):
            ordered_recommended.extend([card for card, _, _, _ in card_by_type[card_type]])

        # Create a global rank order based purely on priority:
        # 1. Auto-includes first
        # 2. Then owned cards
        # 3. Then all other cards
        # All sorted by synergy score within each partition
        global_rank_order = []

        # Auto-includes first, sort by synergy score
        auto_include_cards = [(card, synergy_scores.get(card, 0)) for card in recommended if card in auto_includes]
        auto_include_cards.sort(key=lambda x: -x[1])  # Sort by synergy score descending
        global_rank_order.extend([card for card, _ in auto_include_cards])

        # Then owned cards that aren't auto-includes, sort by synergy score
        owned_cards = [(card, synergy_scores.get(card, 0)) for card in recommended if
                       card in self.owned_cards and card not in auto_includes]
        owned_cards.sort(key=lambda x: -x[1])  # Sort by synergy score descending
        global_rank_order.extend([card for card, _ in owned_cards])

        # Then all other cards, sort by synergy score
        other_cards = [(card, synergy_scores.get(card, 0)) for card in recommended if
                       card not in auto_includes and card not in self.owned_cards]
        other_cards.sort(key=lambda x: -x[1])  # Sort by synergy score descending
        global_rank_order.extend([card for card, _ in other_cards])

        # Create a mapping of card to rank for the global rank
        global_rank_map = {card: idx for idx, card in enumerate(global_rank_order, 1)}

        # Exception for basic lands: we can have duplicates of them
        # Keep track of cards we've already processed by their normalized names
        basic_land_count = Counter()

        # Now create the dataframe from the ordered list
        for idx, card in enumerate(ordered_recommended, 1):
            is_auto_include = card in auto_includes
            is_owned = card in self.owned_cards
            norm_card = self.normalize_card_name(card)

            # For basic lands, we allow duplicates but track the count
            is_basic_land = self.is_basic_land(card)

            # Skip if we've already processed a card with this normalized name
            # UNLESS it's a basic land (which we allow duplicates of)
            if norm_card in processed_normalized_names and not is_basic_land:
                print(f"Skipping duplicate normalized card: {card}")
                continue

            # Mark this normalized name as processed if it's not a basic land
            if not is_basic_land:
                processed_normalized_names.add(norm_card)
            else:
                # For basic lands, track the count
                basic_land_count[norm_card] += 1
                # Add a count suffix for display
                if basic_land_count[norm_card] > 1:
                    card = f"{card} ({basic_land_count[norm_card]})"

            # Get synergy score for this card
            synergy_value = synergy_scores.get(card, 0)

            # Get the global rank
            # For basic lands with counts, use the base name to look up rank
            base_card = card.split(' (')[0] if ' (' in card else card
            global_rank = global_rank_map.get(base_card, 0)

            # If this is an auto-include but also exists in scraped cards with a different case
            # use the frequency from the scraped card
            if norm_card in normalized_card_freq and not is_basic_land:
                scraped_card, freq = normalized_card_freq[norm_card]
                # Use the scraped card name but mark it as an auto-include
                scraped_card_owned = scraped_card in self.owned_cards or card in self.owned_cards

                # Use the card type from auto_include_manager if it's an auto-include card
                if is_auto_include:
                    card_type = self.auto_include_manager.get_card_type(card)
                else:
                    card_type = self.card_types.get(scraped_card, "Unknown")

                # If this is a basic land but card type is Unknown, set to Land
                if card_type == "Unknown" and self.is_basic_land(scraped_card):
                    card_type = "Land"

                deck_data.append({
                    'Rank': global_rank,  # Use global rank for consistent sorting
                    'Card Name': scraped_card,  # Use the scraped card name for consistency
                    'Mana Cost': self.card_mana_costs.get(norm_card, ''),
                    'Frequency': freq,
                    'Card Type': card_type,
                    'Synergy Score': f"{synergy_value:.3f}",  # Format to 3 decimal places
                    'Owned': scraped_card_owned,
                    'Quantity Owned': max(
                        self.card_quantities.get(scraped_card, 0),
                        self.card_quantities.get(card, 0)
                    ),
                    'Auto-Include': is_auto_include
                })
                print(f"Using scraped card '{scraped_card}' (freq: {freq}) instead of auto-include '{card}'")
            else:
                # For auto-includes that don't exist in scraped decks, set frequency to 0
                if is_auto_include:
                    card_type = self.auto_include_manager.get_card_type(card)
                else:
                    base_card_name = card.split(' (')[0] if ' (' in card else card
                    card_type = self.card_types.get(base_card_name, "Unknown")

                # If this is a basic land but card type is Unknown, set to Land
                if card_type == "Unknown" and self.is_basic_land(base_card_name):
                    card_type = "Land"

                deck_data.append({
                    'Rank': global_rank,  # Use global rank for consistent sorting
                    'Card Name': card,
                    'Mana Cost': self.card_mana_costs.get(norm_card, ''),
                    'Frequency': card_frequency.get(card.split(' (')[0] if ' (' in card else card, 0),
                    'Card Type': card_type,
                    'Synergy Score': f"{synergy_value:.3f}",  # Format to 3 decimal places
                    'Owned': is_owned,
                    'Quantity Owned': self.card_quantities.get(card.split(' (')[0] if ' (' in card else card,
                                                               0) if is_owned else 0,
                    'Auto-Include': is_auto_include
                })
                if is_auto_include and card_frequency.get(card, 0) == 0:
                    print(f"Auto-include '{card}' not found in scraped cards (using freq: 0)")

        # Create DataFrame - keep the existing order
        df = pd.DataFrame(deck_data)

        # Sort by Rank to maintain the global rank order
        df = df.sort_values('Rank')

        # Export to CSV
        output_path = f"{self.output_dir}/analysis/recommended_decklist.csv"
        df.to_csv(output_path, index=False)

        print(f"Exported recommended decklist to {output_path}")
        return df

    def get_card_type(self, type_line):
        """
        Extract card type from type_line.

        Args:
            type_line (str): The type line of the card

        Returns:
            str: Simplified card type (Land, Creature, Instant, etc.)
        """
        if not type_line:
            return "Unknown"

        type_line = str(type_line).lower()

        if "land" in type_line:
            return "Land"
        elif "creature" in type_line:
            return "Creature"
        elif "instant" in type_line:
            return "Instant"
        elif "sorcery" in type_line:
            return "Sorcery"
        elif "enchantment" in type_line:
            return "Enchantment"
        elif "artifact" in type_line:
            return "Artifact"
        else:
            return "Unknown"

    def is_basic_land(self, card_name):
        """Check if a card is a basic land based on its name"""
        normalized = self.normalize_card_name(card_name)
        return any(basic in normalized for basic in self.basic_lands)


class AutoIncludeManager:
    def __init__(self, output_dir="moxfield_data"):
        self.output_dir = output_dir
        self.auto_include_file = f"{output_dir}/auto_includes.json"
        self.disabled_file = f"{output_dir}/disabled_auto_includes.json"
        self.auto_include_types_file = f"{output_dir}/auto_include_types.json"
        self.auto_includes = {
            # Single colors
            "WHITE": [],
            "BLUE": [],
            "BLACK": [],
            "RED": [],
            "GREEN": [],
            "GREY": [],  # Colorless/artifact cards that go in any deck
            # Two-color combinations (all alphabetically sorted)
            "BLACK_WHITE": [],
            "BLUE_WHITE": [],
            "GREEN_WHITE": [],
            "RED_WHITE": [],
            "BLACK_BLUE": [],
            "BLUE_RED": [],
            "BLUE_GREEN": [],
            "BLACK_RED": [],
            "BLACK_GREEN": [],
            "GREEN_RED": []
        }

        # Store card types for auto-includes
        self.card_types = {}

        # Track disabled cards for each color
        self.disabled_cards = {color: [] for color in self.auto_includes.keys()}

        print(f"AutoIncludeManager initializing with file: {self.auto_include_file}")

        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")

        if os.path.exists(self.auto_include_file):
            print(f"Auto-include file exists: {self.auto_include_file}")
        else:
            print(f"Auto-include file does not exist, will create new: {self.auto_include_file}")
            # Save default empty lists
            self.save_auto_includes()

        self.load_auto_includes()
        self.load_disabled_cards()
        self.load_card_types()

        print(f"After initialization, GREY auto-includes: {self.auto_includes['GREY']}")
        print(f"Disabled GREY cards: {self.disabled_cards['GREY']}")

        # Debug check all lists
        for color, cards in self.auto_includes.items():
            if cards:
                print(f"Color {color} has {len(cards)} auto-includes: {cards}")

    def load_auto_includes(self):
        """Load auto-include cards from file"""
        if os.path.exists(self.auto_include_file):
            try:
                with open(self.auto_include_file, 'r') as f:
                    loaded_data = json.load(f)
                    print(f"Loaded data from {self.auto_include_file}")

                    # Migrate any old format color pairs to the new sorted format
                    self._migrate_color_pairs(loaded_data)

                    # Ensure all required keys exist
                    for key in self.auto_includes.keys():
                        if key not in loaded_data:
                            print(f"Warning: Key {key} missing from loaded data, initializing as empty list")
                            loaded_data[key] = []

                    self.auto_includes = loaded_data
                    print(f"After loading, GREY auto-includes: {self.auto_includes.get('GREY', [])}")
            except Exception as e:
                print(f"Error loading auto-includes: {e}")
        else:
            print(f"Auto-include file not found: {self.auto_include_file}, using defaults")

    def _migrate_color_pairs(self, data_dict):
        """Migrate color pairs to the new sorted format"""
        # List of old style keys that need migration
        old_keys = ["WHITE_BLUE", "WHITE_BLACK", "WHITE_RED", "WHITE_GREEN",
                    "BLUE_BLACK", "BLUE_RED", "BLUE_GREEN",
                    "BLACK_RED", "BLACK_GREEN", "RED_GREEN"]

        # Map old keys to new keys
        key_mapping = {
            "WHITE_BLUE": "BLUE_WHITE",
            "WHITE_BLACK": "BLACK_WHITE",
            "WHITE_RED": "RED_WHITE",
            "WHITE_GREEN": "GREEN_WHITE",
            "BLUE_BLACK": "BLACK_BLUE",
            "BLUE_RED": "BLUE_RED",  # Already correct
            "BLUE_GREEN": "BLUE_GREEN",  # Already correct
            "BLACK_RED": "BLACK_RED",  # Already correct
            "BLACK_GREEN": "BLACK_GREEN",  # Already correct
            "RED_GREEN": "GREEN_RED"
        }

        for old_key in old_keys:
            if old_key in data_dict and old_key != key_mapping[old_key]:
                # Found an old key that needs migration
                print(f"Migrating data from {old_key} to {key_mapping[old_key]}")

                # If the new key already exists, merge the data
                if key_mapping[old_key] in data_dict:
                    print(f"  Merging with existing {key_mapping[old_key]} data")
                    # Use a set to remove duplicates when merging
                    combined = set(data_dict[old_key] + data_dict[key_mapping[old_key]])
                    data_dict[key_mapping[old_key]] = list(combined)
                else:
                    # Just move the data to the new key
                    data_dict[key_mapping[old_key]] = data_dict[old_key]

                # Remove the old key
                print(f"  Removing old key {old_key}")
                del data_dict[old_key]

    def load_disabled_cards(self):
        """Load disabled cards from file"""
        if os.path.exists(self.disabled_file):
            try:
                with open(self.disabled_file, 'r') as f:
                    loaded_data = json.load(f)
                    print(f"Loaded disabled cards from {self.disabled_file}")

                    # Migrate any old format color pairs to the new sorted format
                    self._migrate_color_pairs(loaded_data)

                    # Ensure all required keys exist
                    for key in self.disabled_cards.keys():
                        if key not in loaded_data:
                            loaded_data[key] = []

                    self.disabled_cards = loaded_data
                    print(f"After loading, disabled GREY cards: {self.disabled_cards.get('GREY', [])}")
            except Exception as e:
                print(f"Error loading disabled cards: {e}")
        else:
            print(f"Disabled cards file not found: {self.disabled_file}, using defaults")

    def load_card_types(self):
        """Load card types from file"""
        if os.path.exists(self.auto_include_types_file):
            try:
                with open(self.auto_include_types_file, 'r') as f:
                    loaded_data = json.load(f)
                    print(f"Loaded card types from {self.auto_include_types_file}")
                    self.card_types = loaded_data
            except Exception as e:
                print(f"Error loading card types: {e}")
        else:
            print(f"Card types file not found: {self.auto_include_types_file}, initializing empty dictionary")
            self.card_types = {}

    def save_auto_includes(self):
        """Save auto-include cards to file"""
        try:
            with open(self.auto_include_file, 'w') as f:
                json.dump(self.auto_includes, f, indent=2)
                print(f"Saved auto-includes to {self.auto_include_file}")
                print(f"After saving, GREY auto-includes: {self.auto_includes.get('GREY', [])}")
        except Exception as e:
            print(f"Error saving auto-includes: {e}")

    def save_disabled_cards(self):
        """Save disabled cards to file"""
        try:
            with open(self.disabled_file, 'w') as f:
                json.dump(self.disabled_cards, f, indent=2)
                print(f"Saved disabled cards to {self.disabled_file}")
        except Exception as e:
            print(f"Error saving disabled cards: {e}")

    def save_card_types(self):
        """Save card types to file"""
        try:
            with open(self.auto_include_types_file, 'w') as f:
                json.dump(self.card_types, f, indent=2)
                print(f"Saved card types to {self.auto_include_types_file}")
        except Exception as e:
            print(f"Error saving card types: {e}")

    def get_auto_includes(self, colors):
        """Get auto-include cards for given colors (excluding disabled ones)"""
        includes = set()
        print(f"\n--- GETTING AUTO-INCLUDES FOR COLORS: {colors} ---")

        # 1. Add single color auto-includes for each selected color
        for color in colors:
            if color in self.auto_includes:
                # Get all cards for this color that aren't disabled
                enabled_cards = [card for card in self.auto_includes[color]
                                 if card not in self.disabled_cards[color]]

                if enabled_cards:
                    print(f"Adding {len(enabled_cards)} {color} auto-includes: {enabled_cards}")
                    if len(enabled_cards) < len(self.auto_includes[color]):
                        print(f"  Skipping {len(self.auto_includes[color]) - len(enabled_cards)} disabled cards")

                    before_count = len(includes)
                    includes.update(enabled_cards)
                    after_count = len(includes)
                    if after_count > before_count:
                        print(f"  Added {after_count - before_count} new cards")
                    else:
                        print(f"  No new cards added (may be duplicates)")
                else:
                    print(f"No enabled {color} auto-includes found")
            else:
                print(f"WARNING: Color {color} not found in auto_includes dictionary")

        # 2. Always include GREY (colorless) cards in any deck
        grey_cards = [card for card in self.auto_includes.get("GREY", [])
                      if card not in self.disabled_cards.get("GREY", [])]

        if grey_cards:
            print(f"Adding {len(grey_cards)} GREY auto-includes: {grey_cards}")
            if len(grey_cards) < len(self.auto_includes.get("GREY", [])):
                print(f"  Skipping {len(self.auto_includes.get('GREY', [])) - len(grey_cards)} disabled GREY cards")

            before_count = len(includes)
            includes.update(grey_cards)
            after_count = len(includes)
            if after_count > before_count:
                print(f"  Added {after_count - before_count} new GREY cards")
            else:
                print(f"  No new GREY cards added (may be duplicates)")
        else:
            print("No enabled GREY auto-includes found")

        # 3. Add two-color auto-includes for every pair of colors in the selection
        if len(colors) >= 2:
            print("Checking two-color combinations:")
            # Debug dump of the auto_includes dictionary keys
            print(f"Available color pairs in auto_includes: {[k for k in self.auto_includes.keys() if '_' in k]}")

            for i in range(len(colors)):
                for j in range(i + 1, len(colors)):
                    color1 = colors[i]
                    color2 = colors[j]
                    # Create a properly normalized color pair
                    color_pair = self.normalize_color_pair(f"{color1}_{color2}")

                    # Special debug for BLUE/BLACK case
                    if set([color1, color2]) == set(["BLUE", "BLACK"]):
                        print(f"DEBUG: Processing BLUE+BLACK pair:")
                        print(f"  - Original colors: {color1}, {color2}")
                        print(f"  - Resulting color_pair: {color_pair}")
                        print(f"  - Exists in auto_includes? {color_pair in self.auto_includes}")
                        print(f"  - 'BLUE_BLACK' exists? {'BLUE_BLACK' in self.auto_includes}")
                        print(f"  - 'BLACK_BLUE' exists? {'BLACK_BLUE' in self.auto_includes}")
                        if color_pair in self.auto_includes:
                            print(f"  - Cards in {color_pair}: {self.auto_includes[color_pair]}")
                        if 'BLUE_BLACK' in self.auto_includes:
                            print(f"  - Cards in BLUE_BLACK: {self.auto_includes['BLUE_BLACK']}")
                        if 'BLACK_BLUE' in self.auto_includes:
                            print(f"  - Cards in BLACK_BLUE: {self.auto_includes['BLACK_BLUE']}")

                    if color_pair in self.auto_includes:
                        # Get all cards for this color pair that aren't disabled
                        pair_cards = [card for card in self.auto_includes[color_pair]
                                      if card not in self.disabled_cards.get(color_pair, [])]

                        if pair_cards:
                            print(f"  Adding {len(pair_cards)} {color_pair} auto-includes: {pair_cards}")
                            if len(pair_cards) < len(self.auto_includes[color_pair]):
                                print(
                                    f"    Skipping {len(self.auto_includes[color_pair]) - len(pair_cards)} disabled cards")

                            before_count = len(includes)
                            includes.update(pair_cards)
                            after_count = len(includes)
                            if after_count > before_count:
                                print(f"    Added {after_count - before_count} new cards from {color_pair}")
                            else:
                                print(f"    No new cards added from {color_pair} (may be duplicates)")
                        else:
                            print(f"  No enabled {color_pair} auto-includes found")
                    else:
                        # Try alternate key format (for backward compatibility)
                        alternate_key = f"{color2}_{color1}" if color1 < color2 else f"{color1}_{color2}"
                        if alternate_key in self.auto_includes:
                            print(f"  Using alternate key format {alternate_key} instead of {color_pair}")
                            # Get all cards for this color pair that aren't disabled
                            pair_cards = [card for card in self.auto_includes[alternate_key]
                                          if card not in self.disabled_cards.get(alternate_key, [])]

                            if pair_cards:
                                print(f"  Adding {len(pair_cards)} {alternate_key} auto-includes: {pair_cards}")
                                if len(pair_cards) < len(self.auto_includes[alternate_key]):
                                    print(
                                        f"    Skipping {len(self.auto_includes[alternate_key]) - len(pair_cards)} disabled cards")

                                before_count = len(includes)
                                includes.update(pair_cards)
                                after_count = len(includes)
                                if after_count > before_count:
                                    print(f"    Added {after_count - before_count} new cards from {alternate_key}")
                                else:
                                    print(f"    No new cards added from {alternate_key} (may be duplicates)")
                            else:
                                print(f"  No enabled {alternate_key} auto-includes found")
                        else:
                            print(f"  WARNING: Color pair {color_pair} not found in auto_includes dictionary")

        # Convert to list for return
        result = list(includes)
        print(f"FINAL RESULT: {len(result)} total auto-includes for {colors}: {result}")
        print(f"--- END AUTO-INCLUDES LOOKUP ---\n")
        return result

    def get_card_type(self, card_name):
        """Get the stored type for a card, or 'Unknown' if not set"""
        return self.card_types.get(card_name, "Unknown")

    def set_card_type(self, card_name, card_type):
        """Set the type for a card"""
        self.card_types[card_name] = card_type
        self.save_card_types()
        return True

    def is_card_enabled(self, color, card_name):
        """Check if a card is enabled for the given color"""
        # First try with the normalized color
        color = self.normalize_color_pair(color)

        if color in self.disabled_cards:
            normalized_name = self.normalize_card_name(card_name)
            for disabled_card in self.disabled_cards[color]:
                if self.normalize_card_name(disabled_card) == normalized_name:
                    return False

        # If the color contains an underscore, try the alternate format too
        if "_" in color:
            parts = color.split("_")
            alternate_key = f"{parts[1]}_{parts[0]}"
            if alternate_key in self.disabled_cards:
                normalized_name = self.normalize_card_name(card_name)
                for disabled_card in self.disabled_cards[alternate_key]:
                    if self.normalize_card_name(disabled_card) == normalized_name:
                        return False

        return True

    def toggle_card_enabled(self, color, card_name, enabled):
        """Enable or disable a card for a color"""
        print(f"Toggling card '{card_name}' for {color} to {enabled}")

        # Handle two-color combinations consistently
        color = self.normalize_color_pair(color)

        if color not in self.auto_includes or color not in self.disabled_cards:
            print(f"Color {color} not found in auto_includes dictionary")
            return False

        # Find exact match in auto_includes
        exact_match = None
        normalized_name = self.normalize_card_name(card_name)
        for card in self.auto_includes[color]:
            if self.normalize_card_name(card) == normalized_name:
                exact_match = card
                break

        if not exact_match:
            print(f"Card '{card_name}' not found in {color} auto-includes")
            return False

        # Update disabled list
        if enabled:
            # Remove from disabled list
            for card in list(self.disabled_cards[color]):
                if self.normalize_card_name(card) == normalized_name:
                    self.disabled_cards[color].remove(card)
                    print(f"Removed '{card}' from disabled list for {color}")
        else:
            # Add to disabled list if not already there
            if exact_match not in self.disabled_cards[color]:
                self.disabled_cards[color].append(exact_match)
                print(f"Added '{exact_match}' to disabled list for {color}")

        self.save_disabled_cards()
        return True

    def add_auto_include(self, color, card_name, card_type="Unknown"):
        """Add a card to auto-includes for a color with optional card type"""
        print(f"Attempting to add card '{card_name}' to color '{color}' with type '{card_type}'")

        # Handle two-color combinations properly
        original_color = color
        color = self.normalize_color_pair(color)
        if original_color != color:
            print(f"Two-color combination detected, normalized from '{original_color}' to: '{color}'")

        if color in self.auto_includes:
            # Normalize card name before adding to be consistent with MoxfieldAnalyzer
            normalized_name = self.normalize_card_name(card_name)
            print(f"Normalized '{card_name}' to '{normalized_name}'")

            if color == "GREY":
                print(f"Adding to GREY category, current GREY cards: {self.auto_includes['GREY']}")

            if normalized_name not in self.auto_includes[color]:
                self.auto_includes[color].append(normalized_name)
                # Store the card type
                self.set_card_type(normalized_name, card_type)
                print(f"Added '{normalized_name}' to {color}, now has {len(self.auto_includes[color])} cards")
                self.save_auto_includes()
                return True
            else:
                print(f"Card '{normalized_name}' already exists in {color}")
        else:
            print(f"Color '{color}' not found in auto_includes dictionary!")
            print(f"Available colors: {list(self.auto_includes.keys())}")

        return False

    def remove_auto_include(self, color, card_name):
        """Remove a card from auto-includes for a color"""
        print(f"Attempting to remove card '{card_name}' from '{color}'")

        # Handle two-color combinations properly
        original_color = color
        color = self.normalize_color_pair(color)
        if original_color != color:
            print(f"Two-color combination detected, normalized from '{original_color}' to: '{color}'")

        if color in self.auto_includes:
            # Normalize the card name for matching
            normalized_name = self.normalize_card_name(card_name)
            print(f"Normalized '{card_name}' to '{normalized_name}'")

            # Get current list of cards for this color
            current_cards = self.auto_includes[color]
            print(f"Current {color} cards: {current_cards}")

            # Find the exact card from the list, if it exists
            exact_match = None
            for existing_card in current_cards:
                if self.normalize_card_name(existing_card) == normalized_name:
                    exact_match = existing_card
                    break

            if exact_match:
                print(f"Found exact match: '{exact_match}', removing")
                self.auto_includes[color].remove(exact_match)
                # Also remove from disabled cards if it exists there
                if color in self.disabled_cards:
                    if exact_match in self.disabled_cards[color]:
                        self.disabled_cards[color].remove(exact_match)
                        print(f"Also removed '{exact_match}' from disabled cards list")
                self.save_auto_includes()
                self.save_disabled_cards()
                return True
            else:
                print(f"Card '{normalized_name}' not found in {color} auto-includes")
        else:
            print(f"Color '{color}' not found in auto_includes dictionary!")

        return False

    def normalize_card_name(self, card_name):
        """Normalize card name to handle variations in naming - matches MoxfieldAnalyzer's method"""
        # Convert to lowercase
        normalized = str(card_name).lower()

        # Remove special characters, but keep spaces
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)

        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def normalize_color_pair(self, color):
        """Normalize a color or color pair to ensure consistent lookup"""
        if "_" in color:
            parts = color.split("_")
            # Always sort alphabetically
            sorted_parts = sorted(parts)
            return f"{sorted_parts[0]}_{sorted_parts[1]}"
        return color


# Run the application as a standalone script
if __name__ == "__main__":
    print("Starting application...")
    try:
        root = tk.Tk()
        app = MoxfieldAnalyzerApp(root)
        print("Application initialized, starting main loop")
        root.mainloop()
        print("Main loop ended")
    except Exception as e:
        import traceback

        print(f"Error starting application: {e}")
        print(traceback.format_exc())
