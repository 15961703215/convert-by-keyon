# from enum import Enum
# import os
# from threading import Thread
# import time
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler, DirCreatedEvent, FileCreatedEvent, DirModifiedEvent, FileModifiedEvent

# from config import WATCH_FOLDER


# class PdfType(Enum):
#     ReviewReport = 1
#     AnaReport = 2


# class PdfHandler(FileSystemEventHandler):

#     def on_created(self, event):
#         print("create")
#         return self.check_pdf(event)

#     def on_modified(self, event):
#         time.sleep(1)
#         print("on_modified")
#         print(event)
#         return self.check_pdf(event)

#     def check_pdf(self, event: DirCreatedEvent | FileCreatedEvent | DirModifiedEvent | FileModifiedEvent):
#         if event.is_directory:
#             return None

#         file_path = event.src_path.lower()
#         if file_path.endswith("_anareport.pdf") or file_path.endswith("_reviewreport.pdf"):
#             filename = os.path.basename(file_path)
#             parts = filename.rsplit('_', 1)
#             recordid = parts[0]
#             pdf_type = PdfType.AnaReport if parts[1] == 'anareport.pdf' else PdfType.ReviewReport
#             self.start_processing(recordid=recordid, pdf_type=pdf_type)

#         return None

#     def start_processing(self, recordid: str, pdf_type: PdfType):
#         """启动后台处理线程"""
#         print("record = %s, type=%s", recordid, pdf_type.name)
#         # try:
#         #     conn = mysql.connector.connect(**DB_CONFIG)
#         #     cursor = conn.cursor()
#         #     cursor.execute(
#         #         "SELECT reqid FROM patient WHERE recordid = %s", (recordid,))
#         #     if (reqid := cursor.fetchone()[0]):
#         #         threading.Thread(
#         #             target=PDFProcessor.check_and_process,
#         #             args=(reqid, recordid)
#         #         ).start()
#         # except Exception as e:
#         #     print(f"启动处理失败: {str(e)}")
#         # finally:
#         #     if conn.is_connected():
#         #         cursor.close()
#         #         conn.close()


# def start_observer(path_to_watch):
#     event_handler = PdfHandler()
#     observer = Observer()
#     observer.schedule(event_handler, path_to_watch, recursive=True)
#     observer.start()

#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#     observer.join()


# def start_async(path_to_watch: str):
#     observer_thread = Thread(target=start_observer, args=(path_to_watch,))
#     # Daemonize thread so it will exit when the main program exits
#     observer_thread.daemon = True
#     observer_thread.start()


# if __name__ == '__main__':
#     os.makedirs(WATCH_FOLDER, exist_ok=True)
#     start_async(WATCH_FOLDER)
#     while True:
#         time.sleep(1)
