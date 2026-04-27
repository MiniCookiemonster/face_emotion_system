def clean_obj_file(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned_lines = []
    for line in lines:
        line = line.strip()  # 去除前后空格
        if line and not line.startswith("#"):  # 过滤空行和注释
            cleaned_lines.append(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned_lines))

    print(f"文件已清理并保存至 {output_path}")


# 运行脚本
if __name__ == "__main__":
    input_file = "data/raw_faces/face_001.obj"  # 替换为 face_001.obj 的路径
    output_file = "data/raw_faces/cleaned_face_001.obj"  # 清理后的文件保存路径

    clean_obj_file(input_file, output_file)