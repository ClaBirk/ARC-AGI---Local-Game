import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import math

# --- Constants ---
SOLUTION_FILENAME = "arc_solutions_log.json" # Stores { "path": ["solved_file1", ...], ... }
ARC_COLORS = ['#000000'] + [plt.cm.rainbow(i/8) for i in range(9)]
ARC_COLORS_HEX = [plt.cm.colors.to_hex(c) if isinstance(c, (tuple, list)) else c for c in ARC_COLORS]

# --- Helper Functions ---

def load_data(file_path):
    # ... (load_data remains the same) ...
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        if 'app' in globals() and app and hasattr(app, 'status_label'):
             app.status_label.config(text=f"Error loading {os.path.basename(file_path)}: {e}")
        else:
             messagebox.showerror("Error", f"Error loading {os.path.basename(file_path)}:\n{e}")
        return None

def plot_matrix_on_canvas(matrix, title, fig, canvas):
    # ... (plot_matrix_on_canvas remains the same) ...
    fig.clear()
    ax = fig.add_subplot(111)
    if matrix is None or matrix.size == 0:
        ax.set_title(f"{title}\n(No data)")
        ax.set_xticks([]); ax.set_yticks([])
        canvas.draw(); return
    rows, cols = matrix.shape
    cmap = plt.cm.colors.ListedColormap(ARC_COLORS)
    bounds = [-0.5 + i for i in range(len(ARC_COLORS) + 1)]
    norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)
    mat = ax.matshow(matrix, cmap=cmap, norm=norm)
    ax.set_title(title, fontsize=10)
    ax.set_xticks(np.arange(-0.5, cols, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, rows, 1), minor=True)
    ax.grid(which='minor', color='grey', linestyle='-', linewidth=0.5)
    ax.tick_params(which='minor', size=0)
    ax.set_xticks(np.arange(cols)); ax.set_yticks(np.arange(rows))
    ax.tick_params(axis='x', bottom=False, top=True, labelbottom=False, labeltop=True, labelsize=8)
    ax.tick_params(axis='y', left=True, right=False, labelleft=True, labelright=False, labelsize=8)
    if rows <= 15 and cols <= 15:
        for i in range(rows):
            for j in range(cols):
                color_index = int(matrix[i, j])
                bgcolor = cmap(norm(color_index))[:3]
                luminance = 0.299*bgcolor[0] + 0.587*bgcolor[1] + 0.114*bgcolor[2]
                text_color = 'white' if luminance < 0.5 else 'black'
                ax.text(j, i, str(color_index), va='center', ha='center', color=text_color, fontsize=6)
    canvas.draw()


# --- Solution Loading/Saving (Handles dict[str, list[str]]) ---
def load_solutions(filename=SOLUTION_FILENAME):
    # ... (load_solutions remains the same) ...
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    print(f"Warning: Invalid format in {filename} (expected dictionary). Starting empty.")
                    return {}
                return data
        except json.JSONDecodeError:
            print(f"Warning: Error decoding {filename}. Starting with empty solutions log.")
            return {}
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}. Starting with empty solutions log.")
            return {}
    return {}

def save_solutions(data, filename=SOLUTION_FILENAME):
    # ... (save_solutions remains the same) ...
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving solutions log to {filename}: {e}")
        messagebox.showerror("Save Error", f"Could not save solutions log to {filename}:\n{e}")
        return False


# --- GUI Application Class ---

class ARCViewerApp:
    def __init__(self, master):
        self.master = master
        master.title("ARC AGI Dataset Viewer & Solver")
        master.geometry("1100x850")

        self.directory_path = tk.StringVar()
        self.selected_file = tk.StringVar()
        self.json_files = []
        self._plot_widgets = []
        self.current_task_data = None
        self.last_test_input_index = -1

        # Interactive Solver State
        self.editable_grid_rows = tk.IntVar(value=5) # Default/Initial size
        self.editable_grid_cols = tk.IntVar(value=5)
        # RESTORE THIS LINE: Initialize the state array here
        self.editable_grid_state = np.zeros((5,5), dtype=int)
        self.current_draw_color = 1
        self.cell_size = 20
        # For flicker reduction: store canvas item IDs
        self._grid_rect_ids = [] # Initialized as empty, populated by create_or_update...
        self._grid_text_ids = [] # Initialized as empty, populated by create_or_update...

        self.solutions = load_solutions()

        # --- Top Frame for File Selection ---
        self.top_frame = ttk.Frame(master, padding="10")
        self.top_frame.pack(fill=tk.X, side=tk.TOP)
        # ... (Directory/File/Progress widgets remain the same) ...
        ttk.Label(self.top_frame, text="Directory:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.dir_entry = ttk.Entry(self.top_frame, textvariable=self.directory_path, width=60)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(self.top_frame, text="Browse...", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(self.top_frame, text="Select File:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.file_combobox = ttk.Combobox(self.top_frame, textvariable=self.selected_file, state="readonly", width=57)
        self.file_combobox.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.file_combobox.bind("<<ComboboxSelected>>", self.load_and_display_all)
        self.progress_label = ttk.Label(self.top_frame, text="Solved: - / - (-.-%)", font=('Helvetica', 10, 'bold'))
        self.progress_label.grid(row=1, column=2, padx=10, pady=5, sticky=tk.E)
        self.top_frame.columnconfigure(1, weight=1)

        # --- Status Bar ---
        self.status_label = ttk.Label(master, text="Load a directory and select a file.", relief=tk.SUNKEN, anchor=tk.W, padding="2 5")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Main Paned Window ---
        self.paned_window = ttk.PanedWindow(master, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # --- Top Pane: Scrollable Display Area ---
        self.display_pane = ttk.Frame(self.paned_window, padding="5")
        self.paned_window.add(self.display_pane, weight=3)
        # ... (Canvas/Scrollbar setup for display remains the same) ...
        self.canvas_display = tk.Canvas(self.display_pane, borderwidth=0)
        self.scrollable_frame_display = ttk.Frame(self.canvas_display)
        self.scrollbar_display = ttk.Scrollbar(self.display_pane, orient="vertical", command=self.canvas_display.yview)
        self.canvas_display.configure(yscrollcommand=self.scrollbar_display.set)
        self.scrollbar_display.pack(side="right", fill="y")
        self.canvas_display.pack(side="left", fill="both", expand=True)
        self.canvas_frame_display_id = self.canvas_display.create_window((0, 0), window=self.scrollable_frame_display, anchor="nw")
        self.scrollable_frame_display.bind("<Configure>", self._on_display_frame_configure)
        self.canvas_display.bind('<Configure>', self._on_display_canvas_configure)
        self.canvas_display.bind("<MouseWheel>", lambda e: self._on_mousewheel(e, self.canvas_display))
        self.canvas_display.bind("<Button-4>", lambda e: self._on_mousewheel(e, self.canvas_display)) # Linux scroll up
        self.canvas_display.bind("<Button-5>", lambda e: self._on_mousewheel(e, self.canvas_display)) # Linux scroll down


        # --- Bottom Pane: Interactive Solver Area ---
        self.solver_pane = ttk.Labelframe(self.paned_window, text=" Interactive Solver (Last Test Output) ", padding="10")
        self.paned_window.add(self.solver_pane, weight=1)

        # --- Solver Control Frame ---
        solver_controls = ttk.Frame(self.solver_pane)
        solver_controls.pack(side=tk.LEFT, fill=tk.Y, padx=10)

        # Dimension Controls
        dim_frame = ttk.Frame(solver_controls)
        dim_frame.pack(pady=5, anchor='w')
        # ... (Row/Col entries and Create/Resize button remain the same) ...
        ttk.Label(dim_frame, text="Rows:").grid(row=0, column=0, padx=2)
        self.rows_entry = ttk.Entry(dim_frame, textvariable=self.editable_grid_rows, width=4)
        self.rows_entry.grid(row=0, column=1, padx=2)
        ttk.Label(dim_frame, text="Cols:").grid(row=0, column=2, padx=2)
        self.cols_entry = ttk.Entry(dim_frame, textvariable=self.editable_grid_cols, width=4)
        self.cols_entry.grid(row=0, column=3, padx=2)
        self.create_grid_button = ttk.Button(dim_frame, text="Create/Resize Grid", command=self.create_or_update_editable_grid, state=tk.DISABLED)
        self.create_grid_button.grid(row=0, column=4, padx=5)


        # Color Palette
        palette_frame = ttk.Frame(solver_controls)
        palette_frame.pack(pady=10, anchor='w')
        # ... (Palette setup remains the same) ...
        ttk.Label(palette_frame, text="Draw Color:").pack(side=tk.LEFT, padx=(0, 5))
        self.color_buttons = []
        for i in range(len(ARC_COLORS_HEX)):
            btn = tk.Button(palette_frame, text=str(i), bg=ARC_COLORS_HEX[i], width=2, height=1,
                            relief=tk.RAISED, command=lambda c=i: self.select_draw_color(c))
            fg_color = 'white' if ARC_COLORS_HEX[i] in ['#000000', '#800080', '#000080'] else 'black'
            btn.config(fg=fg_color)
            btn.pack(side=tk.LEFT, padx=1)
            self.color_buttons.append(btn)
        self.select_draw_color(self.current_draw_color)

        # Check Button (Renamed)
        self.check_button = ttk.Button(solver_controls, text="Check Solution", command=self.check_solution, state=tk.DISABLED)
        self.check_button.pack(pady=10, anchor='w') # Adjusted padding

        # Feedback Label
        self.check_feedback_label = ttk.Label(solver_controls, text="", font=('Helvetica', 10, 'italic'))
        self.check_feedback_label.pack(pady=5, anchor='w')

        # --- Editable Grid Canvas Frame ---
        grid_canvas_frame = ttk.Frame(self.solver_pane)
        grid_canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        self.canvas_edit = tk.Canvas(grid_canvas_frame, bg='white', borderwidth=1, relief=tk.SUNKEN)
        self.canvas_edit.pack(fill=tk.BOTH, expand=True)
        self.canvas_edit.bind("<Button-1>", self.on_grid_click) # Left-click to draw
        self.canvas_edit.bind("<B1-Motion>", self.on_grid_click) # Drag to draw

    # --- Scroll Setup Methods --- (Remain the same)
    def _on_display_frame_configure(self, event=None):
        self.canvas_display.configure(scrollregion=self.canvas_display.bbox("all"))
    def _on_display_canvas_configure(self, event=None):
        canvas_width = self.canvas_display.winfo_width()
        self.canvas_display.itemconfig(self.canvas_frame_display_id, width=canvas_width)
    def _on_mousewheel(self, event, canvas):
        delta = 0
        if event.num == 4: delta = -1
        elif event.num == 5: delta = 1
        elif hasattr(event, 'delta') and event.delta < 0: delta = 1
        elif hasattr(event, 'delta') and event.delta > 0: delta = -1
        if delta != 0:
            y_view = canvas.yview()
            if (delta < 0 and y_view[0] > 0.0) or (delta > 0 and y_view[1] < 1.0):
                 canvas.yview_scroll(delta, "units")

    # --- Core Application Logic ---
    def browse_directory(self):
        # ... (Remains the same, uses normalized path) ...
        dir_path = filedialog.askdirectory()
        if dir_path:
            normalized_dir_path = os.path.normpath(dir_path)
            self.directory_path.set(normalized_dir_path)
            self.find_json_files()
            self.clear_display_area()
            self.disable_solver()
            if not self.json_files:
                 self.status_label.config(text="No .json files found in selected directory.")
                 self.file_combobox['values'] = []; self.selected_file.set("")
            else:
                 self.status_label.config(text="Select a file from the dropdown.")

# --- Inside the ARCViewerApp class ---

    def find_json_files(self):
        """ Finds .json files, stores the full list, filters dropdown to show only unsolved tasks."""
        # Keep self.json_files as the full list of files in the directory
        # Filter only the list shown in the combobox
        all_json_files_in_dir = [] # Store all found files here
        dir_path = self.directory_path.get() # Already normalized

        # Clear previous selections first
        self.selected_file.set("")
        self.file_combobox['values'] = []


        if os.path.isdir(dir_path):
            try:
                # Get all .json files
                all_json_files_in_dir = sorted([
                    f for f in os.listdir(dir_path) if f.lower().endswith('.json')
                ])
                self.json_files = all_json_files_in_dir # Store the full list

                # Get the set of solved files for this directory for efficient lookup
                solved_files_set = set(self.solutions.get(dir_path, []))

                # Filter the list for the combobox (show only unsolved)
                unsolved_files = [
                    f for f in all_json_files_in_dir if f not in solved_files_set
                ]

                # Update the combobox values
                self.file_combobox['values'] = unsolved_files

                # Select the first unsolved file, or clear if all are solved
                if unsolved_files:
                    self.selected_file.set(unsolved_files[0])
                    # Automatically load the first unsolved file
                    # Ensure load_and_display_all is called AFTER the selection is set
                    # Binding <<ComboboxSelected>> might handle this, but explicit call is safer here
                    # Using after(0) ensures the set() completes before loading starts
                    self.master.after(0, self.load_and_display_all)
                else:
                    # All tasks solved or directory empty of JSON files
                    self.clear_display_area() # Clear plots if no file selected
                    self.disable_solver()    # Disable solver
                    if all_json_files_in_dir: # Files exist, but all are solved
                        self.status_label.config(text="All tasks in this directory are marked as solved!")
                    # else: status handled by browse_directory if directory was empty initially

            except Exception as e:
                self.status_label.config(text=f"Error reading directory: {e}")
                self.json_files = [] # Reset full list on error too
                self.selected_file.set("")
                self.file_combobox['values'] = []
        else:
            # Directory path is invalid
            self.json_files = []
            self.selected_file.set("")
            self.file_combobox['values'] = []

        # Update progress based on the full list (self.json_files) vs solutions log
        # This should be called AFTER self.json_files is updated
        self.update_solved_percentage()

    def clear_display_area(self):
        # ... (Remains the same) ...
        for widget in self.scrollable_frame_display.winfo_children(): widget.destroy()
        self._plot_widgets = []
        self.canvas_display.yview_moveto(0)
        self.master.after(10, self._on_display_frame_configure)

    # --- Inside disable_solver method ---
    def disable_solver(self):
        """ Disables solver elements and clears feedback. """
        self.create_grid_button.config(state=tk.DISABLED)
        self.check_button.config(state=tk.DISABLED) # Use new button name
        self.check_feedback_label.config(text="") # Clear feedback
        self.last_test_input_index = -1

        # Set state and IntVars to minimal 1x1
        self.editable_grid_state = np.zeros((1,1), dtype=int)
        self.editable_grid_rows.set(1); self.editable_grid_cols.set(1)

        # Clear canvas items fully
        self.canvas_edit.delete("all")
        # CORRECT Initialisation for 1x1 grid
        self._grid_rect_ids = [[None]]
        self._grid_text_ids = [[None]]

        # Draw the minimal empty 1x1 grid
        self.draw_editable_grid()

    def enable_solver(self, last_test_index, initial_rows, initial_cols):
        """ Enables solver elements, sets initial state, clears feedback. """
        self.last_test_input_index = last_test_index
        self.editable_grid_rows.set(initial_rows)
        self.editable_grid_cols.set(initial_cols)
        self.create_or_update_editable_grid(clear_state=True)
        self.create_grid_button.config(state=tk.NORMAL)
        self.check_button.config(state=tk.NORMAL) # Use new button name
        self.check_feedback_label.config(text="") # Clear feedback


   # --- Inside the ARCViewerApp class ---

    def load_and_display_all(self, event=None):
        """ Loads file, displays ALL examples (Train & Test), prepares solver. """
        file_name = self.selected_file.get()
        current_dir = self.directory_path.get() # Get normalized path
        if not file_name or not current_dir: return

        file_path = os.path.join(current_dir, file_name)
        self.status_label.config(text=f"Loading {file_name}...")
        self.master.update_idletasks()

        self.clear_display_area()
        self.disable_solver() # Disable solver initially

        self.current_task_data = load_data(file_path) # Store current task data
        if not self.current_task_data:
            # Error handling done within load_data or subsequent checks
            self.status_label.config(text=f"Failed to load or parse {file_name}")
            return

        self._plot_widgets = []
        # Use .get with default empty list for safety
        train_examples = self.current_task_data.get('train', [])
        test_examples = self.current_task_data.get('test', [])
        num_train = len(train_examples)
        num_test = len(test_examples)

        if num_train + num_test == 0:
            self.status_label.config(text=f"Loaded {file_name}: No examples found.")
            ttk.Label(self.scrollable_frame_display, text="No examples found in this file.").pack(pady=20)
            # Ensure scroll region is updated even if empty
            self.master.after(10, self._on_display_frame_configure)
            return

        plot_height, plot_width, dpi = 3.5, 3.5, 96

        # --- Plot Training Examples --- (RESTORED BLOCK)
        if num_train > 0:
            train_label = ttk.Label(self.scrollable_frame_display, text="--- Training Examples ---", font=('Helvetica', 12, 'bold'))
            train_label.pack(pady=(10, 5), anchor='w', padx=10)
            self._plot_widgets.append(train_label)

            for i, pair in enumerate(train_examples): # Use the fetched train_examples list
                pair_frame = ttk.Frame(self.scrollable_frame_display, padding=5, relief=tk.GROOVE, borderwidth=1)
                pair_frame.pack(fill=tk.X, pady=5, padx=5)
                self._plot_widgets.append(pair_frame)

                input_matrix = np.array(pair.get('input', []))
                output_matrix = np.array(pair.get('output', []))

                # Input Plot
                fig_in = Figure(figsize=(plot_width, plot_height), dpi=dpi)
                canvas_in = FigureCanvasTkAgg(fig_in, master=pair_frame)
                widget_in = canvas_in.get_tk_widget()
                widget_in.pack(side=tk.LEFT, padx=5, pady=5, expand=False)
                plot_matrix_on_canvas(input_matrix, f"Train {i+1} Input", fig_in, canvas_in)

                # Output Plot
                fig_out = Figure(figsize=(plot_width, plot_height), dpi=dpi)
                canvas_out = FigureCanvasTkAgg(fig_out, master=pair_frame)
                widget_out = canvas_out.get_tk_widget()
                widget_out.pack(side=tk.LEFT, padx=5, pady=5, expand=False)
                plot_matrix_on_canvas(output_matrix, f"Train {i+1} Output", fig_out, canvas_out)

                # Store references
                self._plot_widgets.extend([widget_in, widget_out, canvas_in, canvas_out, fig_in, fig_out])
        # --- End of RESTORED BLOCK ---


        # --- Plot Test Examples --- (Remains the same as last correct version)
        if num_test > 0:
            test_label = ttk.Label(self.scrollable_frame_display, text="--- Test Examples ---", font=('Helvetica', 12, 'bold'))
            test_label.pack(pady=(15, 5), anchor='w', padx=10)
            self._plot_widgets.append(test_label)

            last_test_input_index = num_test - 1

            for i, pair in enumerate(test_examples): # Use the fetched test_examples list
                is_last_test = (i == last_test_input_index)

                pair_frame = ttk.Frame(self.scrollable_frame_display, padding=5, relief=tk.GROOVE, borderwidth=1)
                pair_frame.pack(fill=tk.X, pady=5, padx=5)
                self._plot_widgets.append(pair_frame)

                # Plot Input
                input_matrix = np.array(pair.get('input', []))
                fig_in = Figure(figsize=(plot_width, plot_height), dpi=dpi)
                canvas_in = FigureCanvasTkAgg(fig_in, master=pair_frame)
                widget_in = canvas_in.get_tk_widget()
                widget_in.pack(side=tk.LEFT, padx=5, pady=5, expand=False)
                plot_matrix_on_canvas(input_matrix, f"Test {i+1} Input", fig_in, canvas_in)
                self._plot_widgets.extend([widget_in, canvas_in, fig_in])

                # Plot Output or Placeholder (Always placeholder for last)
                output_matrix = np.array(pair.get('output', [])) if 'output' in pair else None
                if is_last_test or output_matrix is None:
                    ph_text = f"Test {i+1} Output\n(To be predicted)"
                    ph = ttk.Label(pair_frame, text=ph_text, relief=tk.SOLID, padding=10, borderwidth=1, justify=tk.CENTER)
                    ph.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.BOTH)
                    self._plot_widgets.append(ph)
                else:
                    fig_out = Figure(figsize=(plot_width, plot_height), dpi=dpi)
                    canvas_out = FigureCanvasTkAgg(fig_out, master=pair_frame)
                    widget_out = canvas_out.get_tk_widget()
                    widget_out.pack(side=tk.LEFT, padx=5, pady=5, expand=False)
                    plot_matrix_on_canvas(output_matrix, f"Test {i+1} Output", fig_out, canvas_out)
                    self._plot_widgets.extend([widget_out, canvas_out, fig_out])

                # Determine Solver Size and Enable (if last test example)
                if is_last_test:
                    # ... (solver dimension determination logic remains the same) ...
                    expected_rows, expected_cols = 3, 3
                    determined_from_training = False
                    if num_train > 0: # Check training outputs (use num_train check)
                         train_outputs_np = [np.array(tr_pair.get('output', [])) for tr_pair in train_examples] # Use train_examples
                         valid_train_outputs = [out for out in train_outputs_np if out.ndim == 2 and out.size > 0]
                         if valid_train_outputs:
                            first_shape = valid_train_outputs[0].shape
                            if all(out.shape == first_shape for out in valid_train_outputs):
                                expected_rows, expected_cols = first_shape
                                determined_from_training = True
                                print(f"Solver size: Using consistent training output dimensions: {expected_rows}x{expected_cols}")
                            else: print("Solver size: Training output dimensions are inconsistent.")
                    if not determined_from_training: # Fallback to input
                         if input_matrix.ndim == 2 and input_matrix.size > 0:
                            expected_rows, expected_cols = input_matrix.shape
                            print(f"Solver size: Falling back to input dimensions: {expected_rows}x{expected_cols}")
                         else: # Absolute fallback
                             expected_rows, expected_cols = 3, 3
                             print(f"Solver size: Falling back to default dimensions: {expected_rows}x{expected_cols}")
                    self.enable_solver(i, expected_rows, expected_cols)

        # --- Final Updates ---
        self.status_label.config(text=f"Loaded {file_name}: {num_train} train, {num_test} test examples.")
        self.master.update_idletasks()
        self.master.after(10, self._on_display_frame_configure) # Ensure scroll region updates
        self.canvas_display.yview_moveto(0) # Scroll display to top


    # --- Interactive Solver Methods ---
    def select_draw_color(self, color_index):
        # ... (Remains the same) ...
        self.current_draw_color = color_index
        for i, btn in enumerate(self.color_buttons):
            relief = tk.SUNKEN if i == color_index else tk.RAISED
            border = 2 if i == color_index else 1
            btn.config(relief=relief, borderwidth=border)


    def create_or_update_editable_grid(self, clear_state=False):
        """ Resizes internal state, clears canvas, initializes ID storage, and redraws. """
        try:
            rows = int(self.editable_grid_rows.get())
            cols = int(self.editable_grid_cols.get())
            if not (0 < rows <= 50 and 0 < cols <= 50):
                 raise ValueError("Grid dimensions must be between 1 and 50.")
        except ValueError as e:
            messagebox.showerror("Invalid Dimensions", f"Please enter valid integer dimensions (1-50).\n{e}")
            if hasattr(self.editable_grid_state, 'shape'):
                self.editable_grid_rows.set(self.editable_grid_state.shape[0])
                self.editable_grid_cols.set(self.editable_grid_state.shape[1])
            return

        # Always clear canvas items fully on resize/create
        self.canvas_edit.delete("all")
        # Initialize/Resize ID storage before drawing
        self._grid_rect_ids = [[None for _ in range(cols)] for _ in range(rows)]
        self._grid_text_ids = [[None for _ in range(cols)] for _ in range(rows)]

        # Update internal grid state only if size changed or clear requested
        if clear_state or (rows, cols) != self.editable_grid_state.shape:
            print(f"Creating new solver grid state: {rows}x{cols}")
            self.editable_grid_state = np.zeros((rows, cols), dtype=int)
        else:
             # If size is same, ensure state matches new dimensions (e.g., trim/pad if logic was complex)
             # For simple resize, zeros is fine if size changed, otherwise keep existing state
             pass

        # Always redraw the canvas fully after resize/create
        self.draw_editable_grid()


    def draw_editable_grid(self):
        """ Draws the editable grid on the canvas, storing item IDs. """
        # NOTE: Assumes canvas is clear and ID storage (_grid_rect_ids/_grid_text_ids) is sized correctly.
        # Called by create_or_update_editable_grid or root.after_idle initially.
        rows, cols = self.editable_grid_state.shape
        if rows == 0 or cols == 0: return

        self.canvas_edit.update_idletasks()
        canvas_width = self.canvas_edit.winfo_width() - 4
        canvas_height = self.canvas_edit.winfo_height() - 4
        if canvas_width <= 0 or canvas_height <= 0:
             self.master.after(100, self.draw_editable_grid); return # Try again later

        cell_w = max(1, math.floor(canvas_width / cols))
        cell_h = max(1, math.floor(canvas_height / rows))
        self.cell_size = min(cell_w, cell_h, 50)

        grid_width = self.cell_size * cols; grid_height = self.cell_size * rows
        offset_x = max(2, (canvas_width - grid_width) // 2)
        offset_y = max(2, (canvas_height - grid_height) // 2)

        for r in range(rows):
            for c in range(cols):
                x1, y1 = offset_x + c * self.cell_size, offset_y + r * self.cell_size
                x2, y2 = x1 + self.cell_size, y1 + self.cell_size
                color_index = self.editable_grid_state[r, c]
                if not (0 <= color_index < len(ARC_COLORS_HEX)): color_index = 0
                fill_color = ARC_COLORS_HEX[color_index]

                # Create rectangle and store ID
                rect_id = self.canvas_edit.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline='grey', width=1)
                self._grid_rect_ids[r][c] = rect_id

                # Create text and store ID (optional based on size)
                if self.cell_size > 12:
                     text_color = 'white' if fill_color in ['#000000', '#800080', '#000080'] else 'black'
                     text_content = str(color_index)
                     text_id = self.canvas_edit.create_text(x1 + self.cell_size/2, y1 + self.cell_size/2,
                                                            text=text_content, fill=text_color,
                                                            font=('Helvetica', max(6, int(self.cell_size * 0.4))),
                                                            tags=f"cell_{r}_{c}_text") # Add tag for potential easier access
                     self._grid_text_ids[r][c] = text_id
                else:
                    self._grid_text_ids[r][c] = None # No text item for this cell


    def on_grid_click(self, event):
        """ Handles clicks/drags: Updates state and uses itemconfig for minimal redraw. """
        if self.check_button['state'] == tk.DISABLED: return # Use check_button name

        rows, cols = self.editable_grid_state.shape
        if rows <= 0 or cols <= 0: return # Grid not initialized

        # --- Recalculate geometry INSIDE the handler for accuracy ---
        # Ensure canvas dimensions are up-to-date
        self.canvas_edit.update_idletasks()
        canvas_width = self.canvas_edit.winfo_width() - 4 # Account for border? Adjust if needed.
        canvas_height = self.canvas_edit.winfo_height() - 4

        if canvas_width <= 0 or canvas_height <= 0:
            print("Warning: Canvas size invalid in on_grid_click.")
            return # Cannot calculate if canvas size is invalid

        # Recalculate cell size based on current dimensions and grid cols/rows
        # Mirror the logic from draw_editable_grid
        current_cell_w = max(1, math.floor(canvas_width / cols))
        current_cell_h = max(1, math.floor(canvas_height / rows))
        # Use local calculation for cell size for this specific click event
        local_cell_size = min(current_cell_w, current_cell_h, 50) # Use smaller dimension, cap max size

        if local_cell_size <= 0:
            print("Warning: local_cell_size is invalid in on_grid_click.")
            return # Cannot calculate if cell_size is invalid

        # Recalculate offsets using the locally calculated cell size
        current_grid_width = local_cell_size * cols
        current_grid_height = local_cell_size * rows
        current_offset_x = max(2, (canvas_width - current_grid_width) // 2)
        current_offset_y = max(2, (canvas_height - current_grid_height) // 2)
        # --- End Recalculation ---

        # Calculate column and row based on click position relative to grid origin
        # Using the recalculated offsets and the locally calculated cell size
        c = (event.x - current_offset_x) // local_cell_size
        r = (event.y - current_offset_y) // local_cell_size

        # Clamp indices to be within valid range AFTER calculation
        c = max(0, min(cols - 1, c))
        r = max(0, min(rows - 1, r))

        # --- Optional diagnostic prints ---
        # print(f"Click: ({event.x}, {event.y}), CanvasW/H: ({canvas_width+4}, {canvas_height+4})")
        # print(f"GridR/C: ({rows}, {cols}), LocalCellSize: {local_cell_size}")
        # print(f"GridW/H: ({current_grid_width}, {current_grid_height}), OffsetX/Y: ({current_offset_x}, {current_offset_y})")
        # print(f"Clamped Cell: (r={r}, c={c})")
        # --- End diagnostic prints ---


        # Check if the click physical location is roughly within the drawn grid bounds
        # This helps ignore clicks in margin/padding if calculation is slightly off
        click_in_grid_x = (current_offset_x <= event.x < current_offset_x + current_grid_width)
        click_in_grid_y = (current_offset_y <= event.y < current_offset_y + current_grid_height)

        if click_in_grid_x and click_in_grid_y:
            # Update internal state only if color is different
            if self.editable_grid_state[r, c] != self.current_draw_color:
                self.editable_grid_state[r, c] = self.current_draw_color
                new_color_idx = self.current_draw_color
                new_color_hex = ARC_COLORS_HEX[new_color_idx]

                # --- Update Canvas Item using itemconfig ---
                # Check if ID lists have been initialized correctly (should match rows/cols)
                # Add extra safety check for list structure
                if r < len(self._grid_rect_ids) and self._grid_rect_ids[r] is not None and c < len(self._grid_rect_ids[r]):
                    rect_id = self._grid_rect_ids[r][c]
                    if rect_id is not None:
                        self.canvas_edit.itemconfig(rect_id, fill=new_color_hex)
                    else: print(f"Warning: rect_id is None at ({r},{c})") # Debug missing ID
                else:
                    print(f"Warning: rect_id index out of bounds or row not initialized ({r},{c})")

                if r < len(self._grid_text_ids) and self._grid_text_ids[r] is not None and c < len(self._grid_text_ids[r]):
                    text_id = self._grid_text_ids[r][c]
                    if text_id is not None: # Update text only if it exists
                        new_text_color = 'white' if new_color_hex in ['#000000', '#800080', '#000080'] else 'black'
                        self.canvas_edit.itemconfig(text_id, text=str(new_color_idx), fill=new_text_color)
                    # else: print(f"Warning: text_id is None at ({r},{c})") # Text might legitimately be None if cell too small
                else:
                     print(f"Warning: text_id index out of bounds or row not initialized ({r},{c})")

                # Clear feedback label when user draws, as previous check is now invalid
                self.check_feedback_label.config(text="")
        # else: print(f"Click ({event.x},{event.y}) was outside calculated grid bounds") # Optional debug


    def check_solution(self):
        """ Checks the drawn grid against the correct output and provides feedback.
            Only marks as solved if correct. """
        current_file = self.selected_file.get()
        current_dir = self.directory_path.get()

        # --- Basic Checks ---
        if not current_file or not current_dir:
            messagebox.showwarning("No Task", "No directory or task file selected.")
            return
        if self.last_test_input_index < 0:
             messagebox.showwarning("No Test Case", "Solver not linked to a specific test case.")
             return
        if self.current_task_data is None or 'test' not in self.current_task_data:
             messagebox.showerror("Error", "Task data not loaded correctly.")
             return
        if not (0 <= self.last_test_input_index < len(self.current_task_data['test'])):
             messagebox.showerror("Error", "Invalid test case index.")
             return

        # --- Get Correct Output ---
        try:
            correct_pair = self.current_task_data['test'][self.last_test_input_index]
            if 'output' not in correct_pair:
                self.check_feedback_label.config(text="Cannot check: Correct output not available.", foreground="orange")
                messagebox.showinfo("Cannot Check", "The correct output for this test case is not included in the loaded task data.")
                return
            correct_grid_np = np.array(correct_pair['output'])
        except Exception as e:
             messagebox.showerror("Error", f"Could not get correct output data: {e}")
             self.check_feedback_label.config(text="Error accessing correct output.", foreground="red")
             return

        # --- Compare Grids ---
        user_grid_np = self.editable_grid_state
        is_correct = False
        feedback_text = ""
        feedback_color = "red" # Default to incorrect

        if user_grid_np.shape != correct_grid_np.shape:
            feedback_text = f"Incorrect (Wrong dimensions: {user_grid_np.shape} vs {correct_grid_np.shape})"
        elif np.array_equal(user_grid_np, correct_grid_np):
            is_correct = True
            feedback_text = "Correct!"
            feedback_color = "green"
        else:
            feedback_text = "Incorrect (Content mismatch)"

        # --- Update Feedback Label ---
        self.check_feedback_label.config(text=feedback_text, foreground=feedback_color)

        # --- Mark as Solved (only if correct) ---
        if is_correct:
            self._mark_task_as_solved(current_dir, current_file)


# --- Inside the ARCViewerApp class ---

    def _mark_task_as_solved(self, current_dir, current_file):
        """ Internal helper to log task as solved and save. """
        solved_list = self.solutions.setdefault(current_dir, [])
        needs_refresh = False # Flag to check if list actually changed
        if current_file not in solved_list:
            solved_list.append(current_file)
            solved_list.sort()
            needs_refresh = True # Mark that we need to refresh the list later
            # Note: self.solutions is updated here by setdefault/append

        # Always try to save, even if already solved (in case file was corrupt before)
        # But only refresh the list if it was newly added
        if save_solutions(self.solutions, SOLUTION_FILENAME):
            print(f"Task '{current_file}' status updated in solutions log.")
            # Update status bar to confirm it's correct
            status_msg = f"Correct! Task '{current_file}' marked as solved."
            if not needs_refresh:
                 status_msg = f"Correct! (Task was already marked as solved)."
            self.status_label.config(text=status_msg)

            if needs_refresh:
                # Refresh the file list dropdown AFTER saving successfully
                # This also recalculates percentage and loads the next unsolved task
                self.find_json_files()
            else:
                 # If already solved, just update percentage in case json_files list changed
                 self.update_solved_percentage()

        else: # Save failed
             self.status_label.config(text=f"Correct, but failed to save solution log.")
             # Revert the change in memory if save failed AND if it was newly added
             if needs_refresh and current_dir in self.solutions and current_file in self.solutions[current_dir]:
                self.solutions[current_dir].remove(current_file)
                if not self.solutions[current_dir]: del self.solutions[current_dir]


    def update_solved_percentage(self):
        # ... (Remains the same as previous version) ...
        current_dir = self.directory_path.get()
        if not current_dir or not os.path.isdir(current_dir) or not self.json_files:
            self.progress_label.config(text="Solved: - / - (-.-%)"); return
        total_tasks_in_dir = len(self.json_files)
        if total_tasks_in_dir == 0:
             self.progress_label.config(text="Solved: 0 / 0 (0.0%)"); return
        solved_filenames_for_dir = self.solutions.get(current_dir, [])
        present_files_set = set(self.json_files)
        solved_files_set = set(solved_filenames_for_dir)
        solved_count = len(present_files_set.intersection(solved_files_set))
        percent = (solved_count / total_tasks_in_dir) * 100
        progress_text = f"Solved: {solved_count} / {total_tasks_in_dir} ({percent:.1f}%)"
        self.progress_label.config(text=progress_text)


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    # Define app instance globally ONLY if needed by helpers like load_data
    # It's generally better to pass 'app' or 'status_label' explicitly if required
    app = ARCViewerApp(root)

    # Schedule the INITIAL grid creation and drawing AFTER the window is ready
    # This ensures canvas has size and ID lists are correctly initialized.
    root.after_idle(app.create_or_update_editable_grid) # CORRECTED LINE

    root.mainloop()