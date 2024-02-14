import argparse
import os

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from utils.data_manager import DataManager

parser = argparse.ArgumentParser()
parser.add_argument("img_path", type=str, help="Absolute path to image files")
parser.add_argument("data_path", type=str, help="Absolute path to label data")
parser.add_argument(
    "--smart_sort",
    type=bool,
    default=False,
    help="Whether or not to sort predictions by certainty",
)

# Parse command-line arguments
args = parser.parse_args()
images_base_path = args.img_path
metadata_path = args.data_path
smart_sort = args.smart_sort

data_manager = DataManager(metadata_path, images_base_path, smart_sort)

app = Flask(__name__)


@app.route("/images/<path:filename>")
def custom_static(filename):
    return send_from_directory(images_base_path, filename)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_label":
            data_manager.change_label(request.form.get("new_label"))
        elif action == "use_predicted":
            data_manager.use_predicted_label()
        elif action == "next":
            data_manager.next_image()
        elif action == "previous":
            data_manager.previous_image()
        elif action == "delete":
            data_manager.delete_image()
        elif action == "done":
            data_manager.save_changes()
            return redirect(url_for("index"))
    return render_template(
        "index.html",
        data=data_manager.current_data(),
        labels=data_manager.unique_labels(),
        progress=data_manager.get_progress(),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
