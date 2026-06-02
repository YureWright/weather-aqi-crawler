"""
Flask Web 应用 - 空气质量与天气数据爬虫前端
提供可视化界面进行爬取任务管理
"""

import os
import uuid
import threading
import logging
import time
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_file, after_this_request

from crawler import batch_scrape, CITY_TO_PINYIN
from log import run_logger, warning_logger

app = Flask(__name__)

# 任务存储
tasks = {}

# ============================================================
# 日志捕获：通过线程局部变量将日志路由到对应任务的日志列表
# ============================================================

_thread_task_logs = threading.local()


class TaskLogHandler(logging.Handler):
    """将日志记录写入当前线程对应任务的日志列表"""

    def emit(self, record):
        logs = getattr(_thread_task_logs, 'current', None)
        if logs is not None:
            logs.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'level': record.levelname,
                'message': record.getMessage(),
            })


_task_handler = TaskLogHandler()
_task_handler.setFormatter(logging.Formatter('%(message)s'))


def run_crawl_task(task_id: str, city_year_list: list, sleep_interval: float):
    """在后台线程中运行爬虫"""
    # 挂载日志处理器到当前线程
    _thread_task_logs.current = tasks[task_id]["logs"]
    run_logger.addHandler(_task_handler)
    warning_logger.addHandler(_task_handler)

    try:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["progress"] = 0
        tasks[task_id]["message"] = "爬虫启动中..."

        def progress_callback(current, total, message):
            tasks[task_id]["progress"] = int(current / total * 100) if total > 0 else 0
            tasks[task_id]["message"] = message

        # 运行爬虫
        all_data, output_file = batch_scrape(
            city_year_list,
            output_dir="output",
            sleep_interval=sleep_interval,
            progress_callback=progress_callback,
        )

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["message"] = f"✅ 完成！共 {len(all_data)} 条记录"
        tasks[task_id]["output_file"] = output_file
        tasks[task_id]["total_records"] = len(all_data)

    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"❌ 任务失败: {str(e)}"
        app.logger.error(f"任务 {task_id} 失败: {e}", exc_info=True)

    finally:
        # 卸载日志处理器，清理线程局部变量
        run_logger.removeHandler(_task_handler)
        warning_logger.removeHandler(_task_handler)
        _thread_task_logs.current = None


# ============================================================
# 路由
# ============================================================

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html", cities=list(CITY_TO_PINYIN.keys()))


@app.route("/api/start", methods=["POST"])
def start_crawl():
    """启动爬虫任务"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求数据为空"}), 400

    cities = data.get("cities", [])
    years = data.get("years", [])
    sleep_interval = float(data.get("sleep_interval", 2.0))

    if not cities:
        return jsonify({"error": "请选择至少一个城市"}), 400
    if not years:
        return jsonify({"error": "请选择至少一个年份"}), 400

    # 校验城市名
    invalid_cities = [c for c in cities if c not in CITY_TO_PINYIN]
    if invalid_cities:
        return jsonify({"error": f"不支持的城市: {', '.join(invalid_cities)}"}), 400

    # 生成任务
    task_id = uuid.uuid4().hex[:12]
    city_year_list = [(city, year) for city in cities for year in years]

    tasks[task_id] = {
        "id": task_id,
        "status": "queued",
        "progress": 0,
        "message": "排队中...",
        "cities": cities,
        "years": years,
        "total_tasks": len(city_year_list),
        "output_file": None,
        "total_records": 0,
        "logs": [],
    }

    # 启动后台线程
    thread = threading.Thread(
        target=run_crawl_task,
        args=(task_id, city_year_list, sleep_interval),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def get_status(task_id):
    """获取任务状态"""
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    # 只返回最近 200 条日志，减少传输量
    logs = task.get("logs", [])
    if len(logs) > 200:
        logs = logs[-200:]
    return jsonify({
        "id": task["id"],
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "total_records": task.get("total_records", 0),
        "has_output": task.get("output_file") is not None,
        "logs": logs,
    })


@app.route("/api/download/<task_id>")
def download_result(task_id):
    """下载结果文件"""
    task = tasks.get(task_id)
    if not task or not task.get("output_file"):
        return jsonify({"error": "文件不存在"}), 404

    output_file = task["output_file"]
    if not os.path.exists(output_file):
        return jsonify({"error": "文件已过期或已被删除"}), 404

    filename = os.path.basename(output_file)

    @after_this_request
    def cleanup(response):
        # 不在下载后删除文件，让用户有机会重新下载
        return response

    return send_file(
        output_file,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/tasks")
def list_tasks():
    """列出所有任务"""
    task_list = []
    for tid, task in tasks.items():
        task_list.append({
            "id": tid,
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"],
            "cities": task["cities"],
            "years": task["years"],
            "total_records": task.get("total_records", 0),
        })
    # 按创建时间倒序
    task_list.reverse()
    return jsonify(task_list)


@app.route("/api/cities")
def list_cities():
    """返回可用城市列表"""
    return jsonify(list(CITY_TO_PINYIN.keys()))


# 定时清理已完成的任务文件（保留最后10个）
CLEANUP_THRESHOLD = 10


def cleanup_old_tasks():
    """清理旧任务文件和记录"""
    completed = [(tid, t) for tid, t in tasks.items()
                 if t["status"] in ("completed", "failed")]
    if len(completed) > CLEANUP_THRESHOLD:
        to_remove = completed[:-CLEANUP_THRESHOLD]
        for tid, t in to_remove:
            if t.get("output_file") and os.path.exists(t["output_file"]):
                try:
                    os.remove(t["output_file"])
                except OSError:
                    pass
            del tasks[tid]


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    app.run(host="127.0.0.1", port=5000, debug=False)
