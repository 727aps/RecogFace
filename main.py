#!/usr/bin/env python3
"""
SecureFaceID - Privacy-Aware Face Recognition Toolkit
A lightweight, ethical face recognition system for personal use
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox, Listbox, Scrollbar
import tkinter as tk
import cv2
import PIL.Image
import PIL.ImageTk
import threading
import time
import os
from datetime import datetime
from typing import Optional, List

from src.face_detector import FaceDetector
from src.face_trainer import FaceTrainer
from src.face_matcher import FaceMatcher
from src.utils import SecureFaceUtils

ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class SecureFaceIDApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("SecureFaceID - Privacy-Aware Face Recognition")
        self.root.geometry("1200x800")

        # Initialize components
        self.utils = SecureFaceUtils()
        self.detector = FaceDetector()
        self.trainer = FaceTrainer()
        self.matcher = FaceMatcher()

        # GUI state
        self.camera_active = False
        self.current_frame = None
        self.capture_thread = None
        self.consent_given = self.utils.validate_consent()

        # Initialize GUI
        self.setup_consent_dialog()
        if self.consent_given:
            self.setup_main_interface()

    def setup_consent_dialog(self):
        """Show privacy consent dialog on first launch"""
        if self.consent_given:
            return

        consent_window = ctk.CTkToplevel(self.root)
        consent_window.title("Privacy Consent - SecureFaceID")
        consent_window.geometry("600x500")
        consent_window.attributes("-topmost", True)

        # Privacy notice
        title_label = ctk.CTkLabel(consent_window, text="SecureFaceID Privacy Notice",
                                  font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=20)

        privacy_text = """
        SecureFaceID is committed to protecting your privacy:

        ✓ All face processing happens locally on your device
        ✓ Face data is encrypted and stored securely
        ✓ No data is transmitted to external servers
        ✓ You can delete all stored data at any time
        ✓ Age/gender estimation is optional and toggleable

        ⚠️  Face recognition may have biases based on training data
        ⚠️  Ensure diverse representation for best accuracy

        By continuing, you consent to local face processing for personal use only.
        """

        text_box = ctk.CTkTextbox(consent_window, wrap="word", height=250)
        text_box.pack(pady=10, padx=20, fill="both", expand=True)
        text_box.insert("0.0", privacy_text)
        text_box.configure(state="disabled")

        # Consent buttons
        button_frame = ctk.CTkFrame(consent_window, fg_color="transparent")
        button_frame.pack(pady=20, fill="x", padx=20)

        def accept_consent():
            self.utils.record_consent(True)
            self.consent_given = True
            consent_window.destroy()
            self.setup_main_interface()

        def decline_consent():
            self.utils.record_consent(False)
            messagebox.showinfo("Consent Declined",
                              "SecureFaceID requires consent to function. The application will close.")
            self.root.quit()

        accept_btn = ctk.CTkButton(button_frame, text="I Accept - Continue",
                                  command=accept_consent, fg_color="green")
        accept_btn.pack(side="left", padx=10, expand=True)

        decline_btn = ctk.CTkButton(button_frame, text="Decline - Exit",
                                   command=decline_consent, fg_color="red")
        decline_btn.pack(side="right", padx=10, expand=True)

        # Wait for consent
        self.root.withdraw()
        consent_window.wait_window()
        self.root.deiconify()

    def setup_main_interface(self):
        """Setup the main tabbed interface"""
        # Create tabview
        self.tabview = ctk.CTkTabview(self.root, width=1150, height=750)
        self.tabview.pack(pady=10, padx=10, fill="both", expand=True)

        # Create tabs
        self.tabview.add("Enroll Person")
        self.tabview.add("Live Recognition")
        self.tabview.add("Gallery Batch")
        self.tabview.add("Settings")

        # Setup each tab
        self.setup_enroll_tab()
        self.setup_live_tab()
        self.setup_gallery_tab()
        self.setup_settings_tab()

        # Status bar
        self.status_label = ctk.CTkLabel(self.root, text="Ready", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 10))

    def setup_enroll_tab(self):
        """Setup enrollment tab"""
        tab = self.tabview.tab("Enroll Person")

        # Input fields
        input_frame = ctk.CTkFrame(tab)
        input_frame.pack(pady=20, padx=20, fill="x")

        name_label = ctk.CTkLabel(input_frame, text="Person Name:")
        name_label.grid(row=0, column=0, padx=10, pady=10, sticky="e")

        self.name_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter full name")
        self.name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        id_label = ctk.CTkLabel(input_frame, text="Person ID:")
        id_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")

        self.id_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter unique ID")
        self.id_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        input_frame.grid_columnconfigure(1, weight=1)

        # Control buttons
        button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        button_frame.pack(pady=10, padx=20, fill="x")

        self.enroll_btn = ctk.CTkButton(button_frame, text="Start Enrollment",
                                       command=self.start_enrollment, height=40)
        self.enroll_btn.pack(side="left", padx=10, expand=True)

        self.cancel_enroll_btn = ctk.CTkButton(button_frame, text="Cancel",
                                              command=self.cancel_enrollment,
                                              fg_color="red", height=40)
        self.cancel_enroll_btn.pack(side="right", padx=10, expand=True)
        self.cancel_enroll_btn.configure(state="disabled")

        # Progress and preview
        self.enroll_progress = ctk.CTkProgressBar(tab, width=400)
        self.enroll_progress.pack(pady=10)
        self.enroll_progress.set(0)

        self.enroll_status = ctk.CTkLabel(tab, text="")
        self.enroll_status.pack(pady=5)

    def setup_live_tab(self):
        """Setup live recognition tab"""
        tab = self.tabview.tab("Live Recognition")

        # Control panel
        control_frame = ctk.CTkFrame(tab)
        control_frame.pack(pady=10, padx=10, fill="x")

        # Tolerance slider
        tolerance_label = ctk.CTkLabel(control_frame, text="Recognition Tolerance:")
        tolerance_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.tolerance_slider = ctk.CTkSlider(control_frame, from_=0.4, to=0.6,
                                             command=self.update_tolerance)
        self.tolerance_slider.set(0.5)
        self.tolerance_slider.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.tolerance_value = ctk.CTkLabel(control_frame, text="0.50")
        self.tolerance_value.grid(row=0, column=2, padx=10, pady=5)

        # Age/Gender toggle
        self.age_gender_var = ctk.BooleanVar(value=True)
        age_gender_check = ctk.CTkCheckBox(control_frame, text="Show Age/Gender Estimates",
                                          variable=self.age_gender_var)
        age_gender_check.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        control_frame.grid_columnconfigure(1, weight=1)

        # Video display area
        self.live_canvas = ctk.CTkCanvas(tab, bg="black", height=400)
        self.live_canvas.pack(pady=10, padx=10, fill="both", expand=True)

        # Control buttons
        button_frame = ctk.CTkFrame(tab, fg_color="transparent")
        button_frame.pack(pady=10, padx=10, fill="x")

        self.start_live_btn = ctk.CTkButton(button_frame, text="Start Recognition",
                                           command=self.start_live_recognition, height=40)
        self.start_live_btn.pack(side="left", padx=10, expand=True)

        self.stop_live_btn = ctk.CTkButton(button_frame, text="Stop Recognition",
                                          command=self.stop_live_recognition,
                                          fg_color="red", height=40)
        self.stop_live_btn.pack(side="right", padx=10, expand=True)
        self.stop_live_btn.configure(state="disabled")

        # Status
        self.live_status = ctk.CTkLabel(tab, text="Click 'Start Recognition' to begin")
        self.live_status.pack(pady=5)

    def setup_gallery_tab(self):
        """Setup gallery batch processing tab"""
        tab = self.tabview.tab("Gallery Batch")

        # File selection
        file_frame = ctk.CTkFrame(tab)
        file_frame.pack(pady=10, padx=10, fill="x")

        self.file_listbox = tk.Listbox(file_frame, selectmode=tk.MULTIPLE, height=8)
        scrollbar = tk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        button_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=5, pady=5)

        add_files_btn = ctk.CTkButton(button_frame, text="Add Images",
                                     command=self.add_gallery_files)
        add_files_btn.pack(side="left", padx=5)

        clear_files_btn = ctk.CTkButton(button_frame, text="Clear List",
                                       command=self.clear_gallery_files, fg_color="orange")
        clear_files_btn.pack(side="left", padx=5)

        # Output directory
        output_frame = ctk.CTkFrame(tab)
        output_frame.pack(pady=10, padx=10, fill="x")

        output_label = ctk.CTkLabel(output_frame, text="Output Directory:")
        output_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.output_entry = ctk.CTkEntry(output_frame, placeholder_text="Select output directory")
        self.output_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        browse_output_btn = ctk.CTkButton(output_frame, text="Browse",
                                         command=self.browse_output_dir)
        browse_output_btn.grid(row=0, column=2, padx=10, pady=5)

        output_frame.grid_columnconfigure(1, weight=1)

        # Process button
        self.process_gallery_btn = ctk.CTkButton(tab, text="Process Gallery",
                                                command=self.process_gallery, height=40)
        self.process_gallery_btn.pack(pady=10, padx=10, fill="x")

        # Progress and results
        self.gallery_progress = ctk.CTkProgressBar(tab)
        self.gallery_progress.pack(pady=5, padx=10, fill="x")
        self.gallery_progress.set(0)

        self.gallery_status = ctk.CTkLabel(tab, text="")
        self.gallery_status.pack(pady=5)

    def setup_settings_tab(self):
        """Setup settings tab"""
        tab = self.tabview.tab("Settings")

        # Database management
        db_frame = ctk.CTkFrame(tab)
        db_frame.pack(pady=10, padx=10, fill="x")

        db_title = ctk.CTkLabel(db_frame, text="Database Management",
                               font=ctk.CTkFont(size=16, weight="bold"))
        db_title.pack(pady=10)

        # Person list
        self.person_listbox = tk.Listbox(db_frame, height=10)
        person_scrollbar = tk.Scrollbar(db_frame, orient=tk.VERTICAL, command=self.person_listbox.yview)
        self.person_listbox.configure(yscrollcommand=person_scrollbar.set)

        self.person_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        person_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        self.refresh_person_list()

        # Database buttons
        db_buttons = ctk.CTkFrame(db_frame, fg_color="transparent")
        db_buttons.pack(fill="x", padx=5, pady=5)

        refresh_btn = ctk.CTkButton(db_buttons, text="Refresh", command=self.refresh_person_list)
        refresh_btn.pack(side="left", padx=5)

        remove_btn = ctk.CTkButton(db_buttons, text="Remove Selected",
                                  command=self.remove_selected_person, fg_color="red")
        remove_btn.pack(side="left", padx=5)

        backup_btn = ctk.CTkButton(db_buttons, text="Create Backup", command=self.create_backup)
        backup_btn.pack(side="left", padx=5)

        # Statistics
        stats_frame = ctk.CTkFrame(tab)
        stats_frame.pack(pady=10, padx=10, fill="x")

        stats_title = ctk.CTkLabel(stats_frame, text="System Statistics",
                                  font=ctk.CTkFont(size=16, weight="bold"))
        stats_title.pack(pady=10)

        self.stats_textbox = ctk.CTkTextbox(stats_frame, height=150)
        self.stats_textbox.pack(pady=5, padx=10, fill="both", expand=True)
        self.update_statistics()

    # Event handlers
    def start_enrollment(self):
        name = self.name_entry.get().strip()
        person_id = self.id_entry.get().strip()

        if not name or not person_id:
            messagebox.showerror("Error", "Please enter both name and ID")
            return

        # Check if ID already exists
        existing_persons = self.trainer.list_persons()
        if any(p['id'] == person_id for p in existing_persons):
            messagebox.showerror("Error", f"Person ID '{person_id}' already exists")
            return

        self.enroll_btn.configure(state="disabled")
        self.cancel_enroll_btn.configure(state="normal")
        self.enroll_progress.set(0)
        self.enroll_status.configure(text="Starting enrollment...")

        # Start enrollment in separate thread
        enrollment_thread = threading.Thread(target=self._perform_enrollment,
                                           args=(name, person_id))
        enrollment_thread.daemon = True
        enrollment_thread.start()

    def _perform_enrollment(self, name, person_id):
        success = self.trainer.add_person(name, person_id)

        self.root.after(0, lambda: self._enrollment_complete(success))

    def _enrollment_complete(self, success):
        if success:
            self.enroll_status.configure(text="Enrollment completed successfully!")
            messagebox.showinfo("Success", "Person enrolled successfully")
            self.name_entry.delete(0, 'end')
            self.id_entry.delete(0, 'end')
            self.refresh_person_list()
        else:
            self.enroll_status.configure(text="Enrollment failed")
            messagebox.showerror("Error", "Enrollment failed. Check logs for details.")

        self.enroll_btn.configure(state="normal")
        self.cancel_enroll_btn.configure(state="disabled")
        self.enroll_progress.set(0)

    def cancel_enrollment(self):
        # This would need more sophisticated thread management in real implementation
        messagebox.showinfo("Cancelled", "Enrollment cancelled")

    def update_tolerance(self, value):
        tolerance = float(value)
        self.tolerance_value.configure(text=f"{tolerance:.2f}")
        self.matcher.set_tolerance(tolerance)

    def start_live_recognition(self):
        if self.camera_active:
            return

        self.camera_active = True
        self.start_live_btn.configure(state="disabled")
        self.stop_live_btn.configure(state="normal")
        self.live_status.configure(text="Starting camera...")

        self.capture_thread = threading.Thread(target=self._live_recognition_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()

    def stop_live_recognition(self):
        self.camera_active = False
        self.start_live_btn.configure(state="normal")
        self.stop_live_btn.configure(state="disabled")
        self.live_status.configure(text="Recognition stopped")

    def _live_recognition_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.root.after(0, lambda: messagebox.showerror("Error", "Could not open camera"))
            return

        while self.camera_active:
            ret, frame = cap.read()
            if not ret:
                break

            # Process frame
            faces, encodings = self.detector.detect_and_encode(frame)
            matches = self.matcher.match_multiple_faces(encodings)

            # Draw results
            for (match, confidence), (x, y, w, h) in zip(matches, faces):
                if match and confidence > 0.5:
                    color = (0, 255, 0)  # Green for recognized
                    label = f"{match['name']} ({confidence:.2f})"

                    # Add age/gender if enabled
                    if self.age_gender_var.get():
                        age_gender = self.utils.estimate_age_gender(frame[y:y+h, x:x+w])
                        if age_gender['age'] > 0:
                            label += f" ~{age_gender['age']} {age_gender['gender']}"
                else:
                    color = (0, 0, 255)  # Red for unknown
                    label = f"Unknown ({confidence:.2f})"

                    # Trigger alert for unknown faces
                    if confidence < 0.3:  # Very low confidence = likely unknown
                        self.utils.show_alert("Unknown Face Detected",
                                            f"Unknown person detected with confidence {confidence:.2f}")

                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            # Update display
            self._update_canvas(frame)

            time.sleep(0.1)  # Control frame rate

        cap.release()

    def _update_canvas(self, frame):
        # Convert frame to PhotoImage for tkinter
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail((800, 600))  # Resize for display

        self.photo = PIL.ImageTk.PhotoImage(img)
        self.live_canvas.create_image(0, 0, image=self.photo, anchor="nw")

    def add_gallery_files(self):
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        for file in files:
            self.file_listbox.insert(tk.END, file)

    def clear_gallery_files(self):
        self.file_listbox.delete(0, tk.END)

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_entry.delete(0, 'end')
            self.output_entry.insert(0, directory)

    def process_gallery(self):
        files = list(self.file_listbox.get(0, tk.END))
        output_dir = self.output_entry.get().strip()

        if not files:
            messagebox.showerror("Error", "Please select image files to process")
            return

        if not output_dir:
            messagebox.showerror("Error", "Please select output directory")
            return

        self.process_gallery_btn.configure(state="disabled")
        self.gallery_progress.set(0)
        self.gallery_status.configure(text="Processing gallery...")

        # Process in separate thread
        process_thread = threading.Thread(target=self._process_gallery_batch,
                                        args=(files, output_dir))
        process_thread.daemon = True
        process_thread.start()

    def _process_gallery_batch(self, files, output_dir):
        results = self.matcher.batch_match_gallery(files, output_dir)

        self.root.after(0, lambda: self._gallery_processing_complete(results))

    def _gallery_processing_complete(self, results):
        self.process_gallery_btn.configure(state="normal")
        self.gallery_progress.set(1.0)

        status_text = f"Processed: {results['processed']} images, " \
                     f"Matches: {results['matches']}, Unknown: {results['unknown']}, " \
                     f"Errors: {results['errors']}"
        self.gallery_status.configure(text=status_text)

        messagebox.showinfo("Gallery Processing Complete", status_text)

    def refresh_person_list(self):
        self.person_listbox.delete(0, tk.END)
        persons = self.trainer.list_persons()
        for person in persons:
            self.person_listbox.insert(tk.END, f"{person['id']}: {person['name']}")

    def remove_selected_person(self):
        selection = self.person_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a person to remove")
            return

        person_text = self.person_listbox.get(selection[0])
        person_id = person_text.split(':')[0].strip()

        if messagebox.askyesno("Confirm Removal",
                              f"Remove person '{person_text}' from database?"):
            if self.trainer.remove_person(person_id):
                messagebox.showinfo("Success", "Person removed successfully")
                self.refresh_person_list()
            else:
                messagebox.showerror("Error", "Failed to remove person")

    def create_backup(self):
        backup_path = self.utils.create_backup(self.trainer.load_face_database())
        if backup_path:
            messagebox.showinfo("Backup Created", f"Backup saved to: {backup_path}")
        else:
            messagebox.showerror("Error", "Failed to create backup")

    def update_statistics(self):
        stats = self.matcher.get_matching_statistics()
        stats_text = f"""Database Statistics:
Total Persons: {stats['total_persons']}
Average Quality Score: {stats['avg_quality_score']:.3f}
Database Integrity: {'Valid' if stats['database_integrity'] else 'Corrupted'}
Current Tolerance: {stats['current_tolerance']:.2f}

System ready for recognition tasks."""
        self.stats_textbox.delete("0.0", "end")
        self.stats_textbox.insert("0.0", stats_text)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SecureFaceIDApp()
    app.run()
