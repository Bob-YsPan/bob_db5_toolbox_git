import requests
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox, font, Label, PhotoImage
from urllib.parse import quote
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageTk
import sv_ttk

# Import the text definitions from gui_text.py
from gui_text_zh_tw import TEXTS


def fetch_file_data(url):
    """
    Fetches file data from a URL and parses the XML response.

    Args:
        url (str): The URL to fetch data from.

    Returns:
        list: A list of dictionaries containing file information.
    """

    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        file_list = []
        for index, file_element in enumerate(root.findall(".//File")):
            filesize_in_bytes = int(file_element.find("SIZE").text)
            filesize_in_mb = round(filesize_in_bytes / (1024 * 1024), 2)
            file_info = {
                "index": index + 1,
                "filename": file_element.find("NAME").text,
                "filesize": filesize_in_mb,
                "filetime": file_element.find("TIME").text,
                "filepath": file_element.find("FPATH").text,
            }
            file_list.append(file_info)
        return file_list

    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to URL: {e}")
        messagebox.showerror(
            TEXTS["error_msg"], TEXTS["error_connection_failed_message"])
        return []
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return []


def get_available_font():
    """
    Finds the first available font from a list of preferred fonts.

    Returns:
        str: The name of the first available font.
    """

    font_fallback_list = [
        "微軟正黑體",
        "Noto Sans CJK TC",
        "Sans",
    ]  # List of preferred fonts

    for font_name in font_fallback_list:
        if font_name in font.families():  # Check if font is available
            return font_name
    # Return last fallback font if none are found
    return font_fallback_list[-1]


def show_playback_url(filepath):
    """
    Displays a popup window with the playback URL for a file.

    Args:
        filepath (str): The path of the file.
    """

    playback_url = filepath.replace(
        "A:\\", "http://192.168.1.254/").replace("\\", "/")

    try:
        # Fetch preview image
        preview_url = f"{playback_url}/?custom=1&cmd=4001"
        response = requests.get(preview_url)
        response.raise_for_status()
        image_data = response.content
        img = Image.open(BytesIO(image_data))
        photo = ImageTk.PhotoImage(img)

    except Exception as e:
        photo = None
        print(f"Failed to fetch preview image: {e}")

    popup = tk.Toplevel()
    popup.title("Playback URL")
    popup.geometry("500x400")  # Adjust size to accommodate image
    popup.transient()
    popup.grab_set()

    label = ttk.Label(popup, text=TEXTS["playback_url_text"])
    label.pack(pady=5)

    url_entry = ttk.Entry(popup, width=50)
    url_entry.insert(0, playback_url)
    url_entry.pack(pady=5)
    url_entry.configure(state="readonly")

    if photo:
        image_label = Label(popup, image=photo)
        image_label.image = photo  # Keep a reference to prevent garbage collection
        image_label.pack(pady=5)
    else:
        image_label = Label(popup, text=TEXTS["error_no_preview"])
        image_label.pack(pady=5)

    copy_button = ttk.Button(
        popup, text=TEXTS["copy_url_btn_text"], command=lambda: copy_to_clipboard(popup, playback_url))
    copy_button.pack(pady=5)

# Function to copy text to the clipboard


def copy_to_clipboard(popup, text):
    """
    Copies text to the clipboard and displays a success message.

    Args:
        popup (ttk.Toplevel): The popup window.
        text (str): The text to copy.
    """

    popup.clipboard_clear()
    popup.clipboard_append(text)
    popup.update()
    messagebox.showinfo(TEXTS["success_msg"], TEXTS["copy_url_success_msg"])

# Function to send a delete file request


def delete_file(filepath, refresh_func):
    """
    Sends a delete file request to the server and refreshes the file list if successful.

    Args:
        filepath (str): The path of the file to delete.
        refresh_func: A function to refresh the file list.
    """

    encoded_path = quote(filepath)
    delete_url = f"http://192.168.1.254/?custom=1&cmd=4003&str={encoded_path}"

    try:
        response = requests.get(delete_url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        status = root.find(".//Status").text
        if status == "0":
            messagebox.showinfo(
                TEXTS["success_msg"], TEXTS["success_file_deleted_message"] + f"\n{filepath}")
            refresh_func()  # Refresh file list after successful deletion
        else:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_delete_failed_message"] + status + ".")
    except Exception as e:
        messagebox.showerror(
            TEXTS["error_msg"], TEXTS["error_file_delete"].format(e))

# Function to create a tkinter window to display file information, allow sorting, and deletion


def create_file_browser(initial_file_list):
    """
    Creates a tkinter window to display file information, allow sorting, and deletion.

    Args:
        initial_file_list (list): A list of dictionaries containing initial file information.
    """
    root = tk.Tk()
    root.title(TEXTS["title"])
    root.geometry("800x450")
    defaultFont = font.nametofont("TkDefaultFont")
    avaliableFont = get_available_font()
    defaultFont.configure(family=avaliableFont, size=12, weight=font.NORMAL)

    # Create a frame to hold the buttons
    button_frame = ttk.Frame(root)
    button_frame.pack(pady=5, fill=tk.X)

    file_list = initial_file_list

    columns = ("index", "filename", "filesize", "filetime")
    tree = ttk.Treeview(root, columns=columns, show="headings")
    tree.heading("index", text=TEXTS["tree_index_text"],
                 command=lambda: sort_column("index"))
    tree.heading("filename", text=TEXTS["tree_fname_text"],
                 command=lambda: sort_column("filename"))
    tree.heading("filesize", text=TEXTS["tree_fsize_text"],
                 command=lambda: sort_column("filesize"))
    tree.heading("filetime", text=TEXTS["tree_ftime_text"],
                 command=lambda: sort_column("filetime"))

    tree.column("index", width=50, anchor="center")
    tree.column("filename", width=400, anchor="w")
    tree.column("filesize", width=100, anchor="e")
    tree.column("filetime", width=150, anchor="center")

    treev_scrl = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    treev_scrl.pack(side="right", fill="y")
    tree.configure(yscrollcommand=treev_scrl.set)

    def check_connection():
        """
        Pings the device every 10 seconds to keep the connection alive.
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=3016")
            response.raise_for_status()  # Raise an exception for bad status codes
            xmlroot = ET.fromstring(response.text)
            status = xmlroot.find(".//Status").text
            if status == "0":
                # Connection successful
                print("Ping Success.")
            else:
                # Connection failed, handle the error
                print(f"Connection failed: Status code {status}")
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_connection_failed_message"])
                exit()  # Exit the program
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {e}")
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_connection_failed_message"])
            exit()  # Exit the program
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_xml_parsing"])
            exit()  # Exit the program
        # Schedule next task
        check_schedule = root.after(10000, check_connection)

    def update_treeview():
        """
        Updates the Treeview with the current file list.
        """

        tree.delete(*tree.get_children())
        for file in file_list:
            tree.insert("", "end", values=(
                file["index"], file["filename"], file["filesize"], file["filetime"]))

    def refresh_file_list():
        """
        Refreshes the file list by fetching data from the server and updates the Treeview.
        """

        nonlocal file_list
        file_list = fetch_file_data("http://192.168.1.254/?custom=1&cmd=3015")
        if last_sort_column:
            file_list.sort(
                key=lambda x: x[last_sort_column], reverse=last_sort_direction)
        update_treeview()
        check_recording_status()

    # Initialize file list
    update_treeview()

    def on_double_click(event):
        """
        Handles double-click events on the Treeview.
        """

        selected_item = tree.selection()
        if selected_item:
            item_values = tree.item(selected_item[0], "values")
            file = next(
                f for f in file_list if f["index"] == int(item_values[0]))
            show_playback_url(file["filepath"])

    tree.bind("<Double-1>", on_double_click)

    sort_direction = {col: False for col in columns}
    last_sort_column, last_sort_direction = "index", False

    def sort_column(column):
        """
        Sorts the file list by the specified column.
        """

        nonlocal file_list, last_sort_column, last_sort_direction
        reverse = sort_direction[column]
        sort_direction[column] = not reverse
        last_sort_column = column
        last_sort_direction = reverse
        file_list.sort(key=lambda x: x[column], reverse=reverse)
        update_treeview()

    def on_right_click(event):
        """
        Handles right-click events on the Treeview.
        """

        selected_item = tree.identify_row(event.y)
        if selected_item:
            tree.selection_set(selected_item)  # Select the right-clicked item
            item_values = tree.item(selected_item, "values")
            file = next(
                f for f in file_list if f["index"] == int(item_values[0]))
            if messagebox.askyesno(TEXTS["delete_confirmation_title"], TEXTS["delete_confirmation_message"] + file["filename"] + "?"):
                delete_file(file["filepath"], refresh_file_list)

    # Recording status detection
    def check_recording_status():
        """
        Checks the recording status from the server.

        Returns:
            bool: True if recording is in progress, False otherwise.
        """

        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=2016")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            value = int(root.find(".//Value").text)
            if value > 0:
                return True  # Recording in progress
            return False
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_recording_status_message"] + str(e))
            return False

    def toggle_recording(is_recording):
        """
        Toggles the recording status on the server.

        Args:
            is_recording (bool): True if recording is currently in progress, False otherwise.
        """

        try:
            par_value = "0" if is_recording else "1"
            response = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=2001&par={par_value}")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                new_status = not is_recording
                record_button.config(
                    text=TEXTS["record_button_stop"] if new_status else TEXTS["record_button_start"])
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_toggle_recording_message"])
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_toggle_recording_message"] + str(e))

    def check_preview_mode():
        """
        Checks the current preview mode status from the server.

        Returns:
            bool: True if in preview mode, False otherwise.
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=3037")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            value = int(root.find(".//Value").text)
            return value == 3  # True for preview mode, False otherwise
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_preview_mode_message"] + str(e))
            return False

    def toggle_preview_mode(is_preview_mode):
        """
        Toggles the preview mode on the server.

        Args:
            is_preview_mode (bool): True if currently in preview mode, False otherwise.
        """
        try:
            par_value = "1" if is_preview_mode else "2"  # 2 for preview, 1 for recording
            response = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3001&par={par_value}")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                new_status = not is_preview_mode
                preview_mode_button.config(
                    text=TEXTS["preview_mode_button_preview"] if new_status else TEXTS["preview_mode_button_recording"])
                # Switch recording button and live_stream button's state
                record_button.config(
                    state=tk.DISABLED if new_status else tk.NORMAL,
                    text=TEXTS["record_button_start"])
                live_stream_button.config(
                    state=tk.NORMAL if not new_status else tk.DISABLED)
                return new_status
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_toggle_preview_mode_message"])
        except Exception as e:
            messagebox.showerror(TEXTS["error_msg"],
                                 TEXTS["error_toggle_preview_mode_message"] + str(e))
            return is_preview_mode

    def sync_time():
        """
        Synchronizes the time with the server.
        """
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            current_time = datetime.now().strftime("%H:%M:%S")

            # Send date
            response_date = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3005&str={current_date}")
            response_date.raise_for_status()
            root_date = ET.fromstring(response_date.text)
            status_date = root_date.find(".//Status").text

            # Send time
            response_time = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3006&str={current_time}")
            response_time.raise_for_status()
            root_time = ET.fromstring(response_time.text)
            status_time = root_time.find(".//Status").text

            if status_date == "0" and status_time == "0":
                messagebox.showinfo(
                    TEXTS["success_msg"], TEXTS["success_sync_time_message"] + f"{current_date} {current_time}")
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_sync_time_message"])

        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_sync_time_message"] + str(e))

    def get_live_stream_url():
        """
        Fetches the live stream URL from the server and displays it.
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=2019")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            movie_link = root.find(".//MovieLiveViewLink").text

            # Simulate double-click behavior (replace with actual playback logic)
            show_playback_url(movie_link)

        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_live_stream_url_message"] + str(e))

    tree.bind("<Button-3>", on_right_click)

    # Refresh button
    refresh_button = ttk.Button(
        button_frame, text=TEXTS["refresh_button"], command=refresh_file_list)
    refresh_button.pack(side=tk.LEFT, padx=10)

    # Preview Mode Button
    is_preview_mode = check_preview_mode()
    preview_mode_button = ttk.Button(
        button_frame,
        text=TEXTS["preview_mode_button_preview"] if is_preview_mode else TEXTS["preview_mode_button_recording"],
        command=lambda: toggle_preview_mode(check_preview_mode())
    )
    preview_mode_button.pack(side=tk.LEFT, padx=10)

    # Recording toggle button
    is_recording = check_recording_status()
    record_button = ttk.Button(
        button_frame,
        text=TEXTS["record_button_stop"] if is_recording else TEXTS["record_button_start"],
        command=lambda: toggle_recording(check_recording_status()),
    )
    record_button.pack(side=tk.LEFT, padx=10)

    # Initial Recording Button State
    record_button.config(
        state=tk.NORMAL if not is_preview_mode else tk.DISABLED)

    sync_time_button = ttk.Button(
        button_frame,
        text=TEXTS["sync_time_button"],
        command=sync_time
    )
    sync_time_button.pack(side=tk.LEFT, padx=10)

    # Live Stream URL Button
    live_stream_button = ttk.Button(
        button_frame,
        text=TEXTS["live_stream_button"],
        command=get_live_stream_url
    )
    live_stream_button.pack(side=tk.LEFT, padx=10)

    # Initial Live button state
    live_stream_button.config(
        state=tk.NORMAL if not is_preview_mode else tk.DISABLED)

    tree.pack(fill=tk.BOTH, expand=True)
    sv_ttk.set_theme("dark")

    check_schedule = root.after(10000, check_connection)
    root.mainloop()


if __name__ == "__main__":
    url = "http://192.168.1.254/?custom=1&cmd=3015"
    file_data = fetch_file_data(url)
    if file_data:
        create_file_browser(file_data)
    else:
        print("Failed to retrieve file data, please check URL or network connection.")
