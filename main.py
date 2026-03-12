import requests
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox, font, PhotoImage
from tkinter.ttk import Label
from urllib.parse import quote
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageTk
import sv_ttk
import threading
from queue import Queue

# Import the text definitions from gui_text.py
from gui_text import TEXTS

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


def wifi_config_window():
    """
    Creates a popup window for Wi-Fi configuration.
    """
    global show_password
    popup = tk.Toplevel()
    popup.title(TEXTS["wifi_config_title"])
    popup.geometry("400x400")
    #popup.transient()
    popup.wait_visibility() # Make sure grab_set() usable on all system
    popup.grab_set()

    # Label for Wi-Fi SSID
    ssid_label = Label(popup, text=TEXTS["wifi_config_ssid"])
    ssid_label.pack(pady=5)

    # Entry for Wi-Fi SSID
    ssid_entry = ttk.Entry(popup)
    ssid_entry.pack(pady=5)

    # Label for Wi-Fi Password
    password_label = Label(popup, text=TEXTS["wifi_config_password"])
    password_label.pack(pady=5)

    # Entry for Wi-Fi Password
    password_entry = ttk.Entry(popup, show="*")
    password_entry.pack(pady=5)
    show_password = False

    def toggle_password_reveal():
        global show_password
        show_password = not show_password
        password_entry.config(show="" if show_password else "*")
    password_reveal_btn = ttk.Button(
        popup, text=TEXTS["wifi_config_reveal_btn"], command=toggle_password_reveal)
    password_reveal_btn.pack(pady=5)

    # Note text
    note_text = Label(
        popup, text=TEXTS["wifi_config_note_label"])
    note_text.pack(pady=5)

    # Button to send Wi-Fi config
    def send_wifi_config():
        ssid = ssid_entry.get()
        password = password_entry.get()
        if len(password) < 8:
            print(f"WiFi password length check fail.")
            messagebox.showerror(TEXTS["error_msg"],
                                 TEXTS["error_wifi_len_password"])
            return
        error_flag = False
        # Send Wi-Fi SSID
        try:
            response = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3003&str={ssid}")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status != "0":
                error_flag = True
                print(f"Failed to send Wi-Fi SSID: {status}")
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_wifi_config_ssid"])
        except Exception as e:
            error_flag = True
            print(f"Failed to send Wi-Fi SSID: {e}")
            messagebox.showerror(TEXTS["error_msg"],
                                 TEXTS["error_wifi_config_ssid"])

        # Send Wi-Fi Password
        try:
            response = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3004&str={password}")
            response.raise_for_status()
            if status != "0":
                error_flag = True
                print(f"Failed to send Wi-Fi SSID: {status}")
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_wifi_config_ssid"])
        except Exception as e:
            error_flag = True
            print(f"Failed to send Wi-Fi Password: {e}")
            messagebox.showerror(TEXTS["error_msg"],
                                 TEXTS["error_wifi_config_password"])
        if not error_flag:
            messagebox.showinfo(
                TEXTS["success_msg"], TEXTS["wifi_config_setup_success"])

    send_wifi_config_button = ttk.Button(
        popup, text=TEXTS["wifi_config_send_btn"], command=send_wifi_config)
    send_wifi_config_button.pack(pady=5)

    # Button to restart device Wi-Fi
    def restart_wifi():
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=3018")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                messagebox.showinfo(
                    TEXTS["success_msg"], TEXTS["wifi_config_restart_success"])
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_wifi_config_restart"])
        except Exception as e:
            print(f"Failed to restart device Wi-Fi: {e}")
            messagebox.showerror(TEXTS["error_msg"],
                                 TEXTS["error_wifi_config_restart"])

    restart_wifi_button = ttk.Button(
        popup, text=TEXTS["wifi_config_restart_btn"], command=restart_wifi)
    restart_wifi_button.pack(pady=5)

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
        preview_url = f"{playback_url}/?custom=1&cmd=4002"
        response = requests.get(preview_url)
        response.raise_for_status()
        image_data = response.content
        img = Image.open(BytesIO(image_data))
        new_height = int(400 / img.width * img.height)
        img = img.resize(size=(400, new_height),
                         resample=Image.Resampling.BICUBIC)
        photo = ImageTk.PhotoImage(img)

    except Exception as e:
        photo = None
        try:
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            print(f"Failed to fetch preview image: {status}")
        except Exception as e:
            print(f"Failed to fetch preview image: {e}")

    popup = tk.Toplevel()
    popup.title(TEXTS["playback_url_title"])
    popup.geometry("500x500")  # Adjust size to accommodate image
    #popup.transient()
    popup.wait_visibility() # Make sure grab_set() usable on all system
    popup.grab_set()

    label = Label(popup, text=TEXTS["playback_url_text"])
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
            # If enable "refrech after delete, activate this"
            if del_refresh: refresh_func()  # Refresh file list after successful deletion
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

    class ThumbnailManager:
        def __init__(self, tree_widget):
            self.tree = tree_widget
            self.cache = {}
            self.loading_indices = set()
            self.semaphore = threading.Semaphore(3) # 限制併發數
            self.debounce_id = None # 用於紀錄 after 的 ID

        def on_scroll_event(self, *args):
            """處理滾動條事件"""
            if args: self.tree.yview(*args)
            self._trigger_debounce()

        def on_resize_event(self, event=None):
            """處理視窗大小改變事件"""
            # 只有當 Treeview 真的有資料時才觸發，避免啟動時的虛假觸發
            if self.tree.get_children():
                self._trigger_debounce()

        def _trigger_debounce(self):
            """統一的防抖觸發邏輯"""
            if self.debounce_id:
                root.after_cancel(self.debounce_id)
            self.debounce_id = root.after(1000, self._process_visible_area)

        def _process_visible_area(self):
            # ... 保持之前的邏輯：計算 y_top, y_bottom 並下載縮圖 ...
            all_items = self.tree.get_children()
            if not all_items or "loading_placeholder" in all_items: return

            y_top, y_bottom = self.tree.yview()
            total = len(all_items)
            
            # 這裡多加一個緩衝 Buffer，避免邊緣項目沒抓到
            start_idx = max(0, int(y_top * total) - 1)
            end_idx = min(int(y_bottom * total) + 2, total)

            for i in range(start_idx, end_idx):
                item_id = all_items[i]
                if not self.tree.item(item_id, "image") and int(item_id) not in self.loading_indices:
                    file_info = next((f for f in file_list if str(f["index"]) == item_id), None)
                    if file_info:
                        self._start_download(item_id, file_info["filepath"])

        def _start_download(self, item_id, filepath):
            idx = int(item_id)
            self.loading_indices.add(idx)
            
            def worker():
                with self.semaphore:
                    try:
                        # 轉換為預覽圖網址
                        url = filepath.replace("A:\\", "http://192.168.1.254/").replace("\\", "/") + "/?custom=1&cmd=4002"
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            img = Image.open(BytesIO(resp.content))
                            img.thumbnail((160, 90))
                            photo = ImageTk.PhotoImage(img)
                            self.cache[idx] = photo
                            # 更新 UI
                            self.tree.after(0, lambda: self._update_item(item_id, photo))
                    except Exception as e:
                        print(f"Download failed: {e}")
                    finally:
                        self.loading_indices.remove(idx)

            threading.Thread(target=worker, daemon=True).start()

        def _update_item(self, item_id, photo):
            if self.tree.exists(item_id):
                # 設定圖片，並清空 Loading 文字 (text 屬性對應 #0 欄位的文字)
                self.tree.item(item_id, image=photo, text="")

    global current_mode, del_refresh

    root = tk.Tk()
    root.title(TEXTS["title"])
    root.geometry("800x450")
    # Set theme
    sv_ttk.set_theme("dark")

    # Create a frame to hold the buttons
    button_frame = ttk.Frame(root)
    button_frame.pack(pady=5, fill=tk.X)

    button_frame2 = ttk.Frame(root)
    button_frame2.pack(pady=5, fill=tk.X)

    file_list = initial_file_list

    # 1. 增加樣式設定 (設定行高以容納縮圖)
    style = ttk.Style()
    style.configure("Treeview", rowheight=100)

    # 重新定義欄位：將 index 移出第一欄，縮圖由 #0 負責
    columns = ("index", "filename", "filesize", "filetime")
    tree = ttk.Treeview(root, columns=columns, show="tree headings") # 這裡要寫 "tree headings"
    thumb_mgr = ThumbnailManager(tree)
    
    # 設定 #0 欄位為縮圖欄位
    tree.heading("#0", text=TEXTS["tree_thumb_text"])
    tree.column("#0", width=160, anchor="center")

    tree.heading("index", text=TEXTS["tree_index_text"],
                 command=lambda: sort_column("index"))
    tree.heading("filename", text=TEXTS["tree_fname_text"],
                 command=lambda: sort_column("filename"))
    tree.heading("filesize", text=TEXTS["tree_fsize_text"],
                 command=lambda: sort_column("filesize"))
    tree.heading("filetime", text=TEXTS["tree_ftime_text"],
                 command=lambda: sort_column("filetime"))

    tree.column("index", width=50, anchor="center")
    tree.column("filename", width=300, anchor="w")
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
        root.after(10000, check_connection)

    def update_treeview():
        tree.delete(*tree.get_children())
        for file in file_list:
            # 初始狀態：text="載入中..." 會顯示在 #0 欄位，直到 image 被載入為止
            tree.insert("", "end", iid=file["index"], text=TEXTS["loading_text"], 
                        values=(file["index"], file["filename"], file["filesize"], file["filetime"]))
        # 手動觸發一次可見區域檢查
        thumb_mgr._process_visible_area()

    # 1. 綁定視窗大小改變事件 (Configure)
    tree.bind("<Configure>", thumb_mgr.on_resize_event)

    # 2. 綁定滾動條 (Scrollbar)
    treev_scrl.config(command=thumb_mgr.on_scroll_event)
    tree.configure(yscrollcommand=treev_scrl.set)

    # 3. 綁定滑鼠滾輪 (MouseWheel)
    tree.bind("<MouseWheel>", lambda e: thumb_mgr.on_scroll_event())

    def update_functional_buttons():
        """根據目前的設備模式 (current_mode) 決定按鈕可用性"""
        try:
            # 錄影按鈕：僅在錄影模式 (0, 1) 可用
            is_recording_mode = (current_mode == 0 or current_mode == 1)
            record_button.config(
                state=tk.NORMAL if is_recording_mode else tk.DISABLED,
                text=TEXTS["record_button_stop"] if (is_recording_mode and check_recording_status()) else TEXTS["record_button_start"]
            )

            # 拍照按鈕：僅在拍照模式 (4) 可用
            take_picture_button.config(
                state=tk.NORMAL if current_mode == 4 else tk.DISABLED
            )

            # 串流按鈕：除了檢視模式 (3) 以外皆可用
            live_stream_button.config(
                state=tk.NORMAL if current_mode != 3 else tk.DISABLED
            )
        except Exception as e:
            print(f"Update functional buttons failed: {e}")

    def set_ui_state(state):
        """控制介面鎖定狀態 (網路存取時調用)"""
        # 基本 Treeview 鎖定
        tree.configure(selectmode='none' if state == tk.DISABLED else 'browse')
        
        # 1. 處理永遠可以點擊或無條件鎖定的按鈕
        for btn in [refresh_button, toggle_mode_button, sync_time_button, 
                    wifi_config_button, del_refresh_btn, view_button]:
            try: btn.config(state=state)
            except: pass

        # 2. 如果是恢復 (NORMAL)，則進行第二次「模式檢查」，決定特定功能的按鈕狀態
        if state == tk.NORMAL:
            update_functional_buttons()
        else:
            # 如果是鎖定 (DISABLED)，直接強制關閉特定功能按鈕
            record_button.config(state=tk.DISABLED)
            take_picture_button.config(state=tk.DISABLED)
            live_stream_button.config(state=tk.DISABLED)

    def refresh_file_list():
        """非同步重新整理檔案列表"""
        # 1. 進入載入狀態
        set_ui_state(tk.DISABLED)
        tree.delete(*tree.get_children())
        # 在第一行顯示載入中訊息
        tree.insert("", "end", iid="loading_placeholder", text=TEXTS["loading_list_text"])

        def worker():
            nonlocal file_list
            try:
                # 執行原本的網路獲取動作
                new_data = fetch_file_data("http://192.168.1.254/?custom=1&cmd=3015")
                
                # 回到主執行緒更新 UI
                root.after(0, lambda: finalize_refresh(new_data))
            except Exception as e:
                root.after(0, lambda: messagebox.showerror(TEXTS["error_msg"], str(e)))
                root.after(0, lambda: set_ui_state(tk.NORMAL))

        def finalize_refresh(new_data):
            nonlocal file_list
            file_list = new_data
            if last_sort_column:
                file_list.sort(key=lambda x: x.get(last_sort_column, 0), reverse=last_sort_direction)
            
            # 2. 清除暫存文字並填入正式資料
            tree.delete(*tree.get_children())
            update_treeview()
            
            # 3. 恢復介面
            set_ui_state(tk.NORMAL)
            # 載入完成後觸發一次縮圖掃描
            thumb_mgr.on_scroll_event()

        # 啟動執行緒
        threading.Thread(target=worker, daemon=True).start()

    # Initialize file list
    # update_treeview()

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
    last_sort_column, last_sort_direction = "filetime", True

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
            response = requests.get("http://192.168.1.254/?custom=1&cmd=3037")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            value = int(root.find(".//Value").text)
            if status != "0":
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_recording_status_message"] + status)
                return False
            if value == 1:
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

    def check_mode():
        """
        Checks the current review mode status from the server.

        Returns:
            int: 
                0, 1: Recording mode
                3: Review mode
                4: Photo mode
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=3037")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            value = int(root.find(".//Value").text)
            print(f"Current mode number: {value}")
            return value
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_toggle_mode_message"] + str(e))
            return None  # Return None on error

    def toggle_mode(current_mode):
        """
        Toggles the review mode on the server.

        Args:
            current_mode (int): Current mode (0, 1: Recording, 3: Review, 4: Photo)

        Returns:
            int: New mode after toggling
        """
        try:
            if current_mode == 0 or current_mode == 1:  # Recording -> Photo
                par_value = "0"
            elif current_mode == 4:  # Photo -> Review
                par_value = "2"
            else:  # Review -> Recording
                par_value = "1"

            response = requests.get(
                f"http://192.168.1.254/?custom=1&cmd=3001&par={par_value}")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                if current_mode == 0 or current_mode == 1:
                    return 4  # Switch to Photo mode
                elif current_mode == 4:
                    return 3  # Switch to Review mode
                else:
                    return 0  # Switch to Recording mode
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_toggle_mode_message"])
                return current_mode
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_toggle_mode_message"] + str(e))
            return current_mode

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

    def get_live_stream_url(current_mode):
        """
        Fetches the live stream URL from the server and displays it.

        Args:
            current_mode (int): Current mode (0: Recording, 3: Review, 4: Photo)
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=2019")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            if current_mode == 0 or current_mode == 1:
                movie_link = root.find(".//MovieLiveViewLink").text
            elif current_mode == 4:
                movie_link = root.find(".//PhotoLiveViewLink").text
            show_playback_url(movie_link)
        except Exception as e:
            messagebox.showerror(
                TEXTS["error_msg"], TEXTS["error_live_stream_url_message"] + str(e))

    def take_picture():
        """
        Sends the command to take a picture.
        """
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=1001")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                messagebox.showinfo(
                    TEXTS["success_msg"], TEXTS["take_pic_success"])
            else:
                messagebox.showerror(
                    TEXTS["error_msg"], TEXTS["error_take_pic"])
        except Exception as e:
            print(f"Failed to take picture: {e}")
            messagebox.showerror(TEXTS["error_msg"], TEXTS["error_take_pic"])

    # Helper function for getting mode text
    def get_mode_text(mode):
        if mode == 0 or mode == 1:
            return TEXTS["toggle_mode_button_recording"]
        elif mode == 3:
            return TEXTS["toggle_mode_button_review"]
        elif mode == 4:
            return TEXTS["toggle_mode_button_photo"]
        else:
            return TEXTS["toggle_mode_button_unknown"]

    # Initial refresh after delete state
    del_refresh = True

    def del_refresh_toggle():
        global del_refresh
        # Filp status
        del_refresh = not del_refresh
        # Update button text
        del_refresh_btn.config(
            text=TEXTS["del_refresh_on"] if del_refresh else TEXTS["del_refresh_off"]
        )


    tree.bind("<Button-3>", on_right_click)

    tree.pack(fill=tk.BOTH, expand=True)

    # Refresh button
    refresh_button = ttk.Button(
        button_frame, text=TEXTS["refresh_button"], command=refresh_file_list)
    refresh_button.pack(side=tk.LEFT, padx=10)

    # Get initial mode
    current_mode = check_mode()

    # Review Mode Button
    toggle_mode_button = ttk.Button(
        button_frame,
        text=get_mode_text(current_mode),  # Use helper function for text
        command=lambda: update_mode(toggle_mode(current_mode))
    )
    toggle_mode_button.pack(side=tk.LEFT, padx=10)

    # Get initial recording status
    recording_status = check_recording_status()

    # Recording toggle button
    record_button = ttk.Button(
        button_frame,
        text=TEXTS["record_button_stop"] if recording_status else TEXTS["record_button_start"],
        command=lambda: toggle_recording(check_recording_status()),
        state=tk.NORMAL if current_mode == 0 or current_mode == 1 else tk.DISABLED
    )
    record_button.pack(side=tk.LEFT, padx=10)

    # Take Picture button
    take_picture_button = ttk.Button(
        button_frame,
        text=TEXTS["take_pic_btn"],
        command=take_picture,
        state=tk.NORMAL if current_mode == 4 else tk.DISABLED
    )
    take_picture_button.pack(side=tk.LEFT, padx=10)

    # Helper function for updating mode and button states
    def update_mode(new_mode):
        global current_mode
        current_mode = new_mode
        toggle_mode_button.config(text=get_mode_text(current_mode))
        set_ui_state(tk.NORMAL)

    # Live Stream URL Button
    live_stream_button = ttk.Button(
        button_frame,
        text=TEXTS["live_stream_button"],
        command=lambda: get_live_stream_url(current_mode),
        state=tk.NORMAL if current_mode != 3 else tk.DISABLED
    )
    live_stream_button.pack(side=tk.LEFT, padx=10)

    sync_time_button = ttk.Button(
        button_frame2,
        text=TEXTS["sync_time_button"],
        command=sync_time
    )
    sync_time_button.pack(side=tk.LEFT, padx=10)

    wifi_config_button = ttk.Button(
        button_frame2, text=TEXTS["wifi_config_btn"], command=wifi_config_window)
    wifi_config_button.pack(side=tk.LEFT, padx=10)

    del_refresh_btn = ttk.Button(
        button_frame2, 
        text=TEXTS["del_refresh_on"] if del_refresh else TEXTS["del_refresh_off"], 
        command=del_refresh_toggle)
    del_refresh_btn.pack(side=tk.LEFT, padx=10)

    # 紀錄目前視角狀態 (0: 前, 1: 後, 2: 雙)
    current_view = 2 

    def set_camera_view(view_mode):
        """傳送指令切換視角"""
        nonlocal current_view
        try:
            response = requests.get(f"http://192.168.1.254/?custom=1&cmd=3028&par={view_mode}")
            response.raise_for_status()
            root_xml = ET.fromstring(response.text)
            status = root_xml.find(".//Status").text
            
            if status == "0":
                current_view = view_mode
                update_view_button_text()
            else:
                print(f"Failed to set view: {status}")
        except Exception as e:
            print(f"Error setting camera view: {e}")

    def toggle_view():
        """循環切換視角：0 -> 1 -> 2 -> 0"""
        next_view = (current_view + 1) % 3
        set_camera_view(next_view)

    # 在 button_frame2 內新增按鈕
    view_button = ttk.Button(
        button_frame2, 
        text=TEXTS["view_dual"], # 預設文字
        command=toggle_view
    )
    view_button.pack(side=tk.LEFT, padx=10)

    def update_view_button_text():
        """根據狀態更新按鈕文字"""
        mapping = {
            0: TEXTS["view_front"],
            1: TEXTS["view_rear"],
            2: TEXTS["view_dual"]
        }
        view_button.config(text=mapping.get(current_view, TEXTS["view_unknown"]))

    # 1. 確保初始顯示「載入中」狀態
    tree.delete(*tree.get_children())
    tree.insert("", "end", iid="loading_placeholder", text=TEXTS["loading_list_text"])
    
    # 2. 鎖定 UI 避免在初次載入時被操作
    set_ui_state(tk.DISABLED)

    # 在 create_file_browser 結尾處的初始化邏輯
    def initial_setup():
        # 1. 啟動時強制切換到雙鏡頭 (par=2)
        set_camera_view(2)
        # 2. 接著執行原本的檔案清單獲取
        refresh_file_list()

    # 原本是 root.after(100, refresh_file_list) 改為：
    root.after(1000, initial_setup)
    # Check schedule
    root.after(10000, check_connection)
    root.mainloop()

if __name__ == "__main__":
    create_file_browser([])
