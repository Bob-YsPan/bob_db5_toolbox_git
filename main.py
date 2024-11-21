import requests
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.parse import quote

# [功能標籤] 從 URL 取得 XML 內容並解析
def fetch_file_data(url):
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
        print(f"無法連接 URL: {e}")
        return []
    except ET.ParseError as e:
        print(f"XML 解析錯誤: {e}")
        return []

# [功能標籤] 顯示播放 URL 的彈窗
def show_playback_url(filepath):
    playback_url = filepath.replace("A:\\", "http://192.168.1.254/").replace("\\", "/")
    popup = tk.Toplevel()
    popup.title("播放 URL")
    popup.geometry("400x100")
    popup.transient()
    popup.grab_set()

    label = tk.Label(popup, text="播放 URL:")
    label.pack(pady=5)

    url_entry = tk.Entry(popup, width=50)
    url_entry.insert(0, playback_url)
    url_entry.pack(pady=5)
    url_entry.configure(state="readonly")

    copy_button = tk.Button(popup, text="複製 URL", command=lambda: copy_to_clipboard(popup, playback_url))
    copy_button.pack(pady=5)

# [功能標籤] 複製文字到剪貼簿
def copy_to_clipboard(popup, text):
    popup.clipboard_clear()
    popup.clipboard_append(text)
    popup.update()
    messagebox.showinfo("成功", "URL 已複製到剪貼簿")

# [功能標籤] 發送刪除檔案請求
def delete_file(filepath, refresh_func):
    encoded_path = quote(filepath)
    delete_url = f"http://192.168.1.254/?custom=1&cmd=4003&str={encoded_path}"

    try:
        response = requests.get(delete_url)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        status = root.find(".//Status").text
        if status == "0":
            messagebox.showinfo("成功", f"檔案已刪除：\n{filepath}")
            refresh_func()  # 刪除成功後刷新列表
        else:
            messagebox.showerror("錯誤", f"刪除失敗，返回碼 {status}。")
    except Exception as e:
        messagebox.showerror("錯誤", f"無法刪除檔案：{e}")

# [功能標籤] 建立 tkinter 視窗顯示檔案資訊，允許排序及刪除
def create_file_browser(initial_file_list):
    root = tk.Tk()
    root.title("LOOKING DB5 工具箱")
    root.geometry("800x450")

    # Create a frame to hold the buttons
    button_frame = tk.Frame(root)
    button_frame.pack(pady=5, fill=tk.X)

    file_list = initial_file_list

    columns = ("index", "filename", "filesize", "filetime")
    tree = ttk.Treeview(root, columns=columns, show="headings")
    tree.heading("index", text="索引", command=lambda: sort_column("index"))
    tree.heading("filename", text="檔名", command=lambda: sort_column("filename"))
    tree.heading("filesize", text="檔案大小 (MB)", command=lambda: sort_column("filesize"))
    tree.heading("filetime", text="檔案時間", command=lambda: sort_column("filetime"))

    tree.column("index", width=50, anchor="center")
    tree.column("filename", width=400, anchor="w")
    tree.column("filesize", width=100, anchor="e")
    tree.column("filetime", width=150, anchor="center")

    treev_scrl = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    treev_scrl.pack(side="right", fill="y")
    tree.configure(yscrollcommand = treev_scrl.set)

    def update_treeview():
        tree.delete(*tree.get_children())
        for file in file_list:
            tree.insert("", "end", values=(file["index"], file["filename"], file["filesize"], file["filetime"]))


    def refresh_file_list():
        nonlocal file_list
        file_list = fetch_file_data("http://192.168.1.254/?custom=1&cmd=3015")
        if last_sort_column:
            file_list.sort(key=lambda x: x[last_sort_column], reverse=last_sort_direction)
        update_treeview()
        check_recording_status()

    # 初始化檔案列表
    update_treeview()

    def on_double_click(event):
        selected_item = tree.selection()
        if selected_item:
            item_values = tree.item(selected_item[0], "values")
            file = next(f for f in file_list if f["index"] == int(item_values[0]))
            show_playback_url(file["filepath"])

    tree.bind("<Double-1>", on_double_click)

    sort_direction = {col: False for col in columns}
    last_sort_column, last_sort_direction = "index", False
    def sort_column(column):
        nonlocal file_list, last_sort_column, last_sort_direction
        reverse = sort_direction[column]
        sort_direction[column] = not reverse
        last_sort_column = column
        last_sort_direction = reverse
        file_list.sort(key=lambda x: x[column], reverse=reverse)
        update_treeview()

    def on_right_click(event):
        selected_item = tree.identify_row(event.y)
        if selected_item:
            tree.selection_set(selected_item)  # 選中右鍵點擊的項目
            item_values = tree.item(selected_item, "values")
            file = next(f for f in file_list if f["index"] == int(item_values[0]))
            if messagebox.askyesno("刪除確認", f"確定刪除此檔案？\n{file['filename']}"):
                delete_file(file["filepath"], refresh_file_list)

    # 錄影狀態偵測
    def check_recording_status():
        try:
            response = requests.get("http://192.168.1.254/?custom=1&cmd=2016")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            value = int(root.find(".//Value").text)
            if value > 0:
                return True  # 正在錄影
            return False
        except Exception as e:
            messagebox.showerror("錯誤", f"無法檢測錄影狀態：{e}")
            return False

    def toggle_recording(is_recording):
        try:
            par_value = "0" if is_recording else "1"
            response = requests.get(f"http://192.168.1.254/?custom=1&cmd=2001&par={par_value}")
            response.raise_for_status()
            root = ET.fromstring(response.text)
            status = root.find(".//Status").text
            if status == "0":
                new_status = not is_recording
                record_button.config(text="停止錄影" if new_status else "開始錄影")
            else:
                messagebox.showerror("錯誤", "切換錄影狀態失敗，請檢查伺服器回應。")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法切換錄影狀態：{e}")

    tree.bind("<Button-3>", on_right_click)

    # 刷新按鈕
    refresh_button = tk.Button(button_frame, text="刷新", command=refresh_file_list)
    refresh_button.pack(side=tk.LEFT, padx=10)

    # 錄製切換鈕
    is_recording = check_recording_status()
    record_button = tk.Button(
    button_frame, 
    text="停止錄影" if is_recording else "開始錄影", 
    command=lambda: toggle_recording(check_recording_status())
    )
    record_button.pack(side=tk.LEFT, padx=10)

    tree.pack(fill=tk.BOTH, expand=True)
    root.mainloop()

if __name__ == "__main__":
    url = "http://192.168.1.254/?custom=1&cmd=3015"
    file_data = fetch_file_data(url)
    if file_data:
        create_file_browser(file_data)
    else:
        print("無法取得檔案資料，請檢查 URL 或網路連線。")
