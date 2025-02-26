import os
import queue
import threading
import time
from pdf2image import convert_from_path

from config import POPPLER_PATH, PUBLIC_FOLDER, WATCH_FOLDER


def convert_pdf_to_jpg(pdf_path, target_path, prefix=""):
    """pdf 转换成图片并返回图片list"""
    try:
        images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

        # 如果不存在, 创建文件夹
        os.makedirs(target_path, exist_ok=True)

        pages = []

        # 保存页面并生成URL
        for page_num, image in enumerate(images, start=1):
            filename = f"{prefix}_{page_num}.jpg"
            output_path = os.path.join(target_path, filename)
            image.save(output_path, "JPEG", quality=90)
            pages.append(filename)

        return pages

    except Exception as e:
        print(f"PDF转换失败: {str(e)}")
        raise


# task_queue = queue.Queue()


# def task_processor(task):
#     print(f"Processing task: {task}")
#     time.sleep(2)  # Simulate task processing time
#     print(f"Finished task: {task}")


# def worker(task_queue: queue.Queue,):
#     while True:
#         print(f"geting task:")
#         task = task_queue.get(True)  # Get the next task from the queue
#         print(f"get task: {task}")
#         task_processor(task)
#         task_queue.task_done()  # Mark the task as done


# num_workers = 1
# threads = []


# def start_queue():
#     for _ in range(num_workers):
#         t = threading.Thread(target=worker, args=(task_queue,), daemon=True)
#         threads.append(t)
#         t.start()


# def wait_queue():
#     for t in threads:
#         t.join()


# if __name__ == '__main__':
#     # pages = convert_pdf_to_jpg(
#     #     os.path.join(WATCH_FOLDER, "test.pdf"),
#     #     os.path.join(PUBLIC_FOLDER, "1")
#     # )
#     # print(pages)

#     time.sleep(5)
#     print("hhhccc")
