import streamlit as st
import google.generativeai as genai
import os
import tempfile
import zipfile
import io
import logging
import threading  # 导入线程模块
import time

# 设置默认 API 密钥
# DEFAULT_API_KEY = "AIzaSyA3CqZkzZbGvSiUSOoNW_P6e1wGiXtl4_o"  # 已移除硬编码的默认密钥

# 配置日志记录
class StreamlitHandler(logging.Handler):
    def __init__(self, log_area, level=logging.NOTSET):
        super().__init__(level)
        self.log_area = log_area
        self.log_text = ""

    def emit(self, record):
        msg = self.format(record)
        self.log_text += msg + "\n"
        self.log_area.text(self.log_text)


def create_logger(log_area):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # 设置日志级别为 INFO 或更低级别
    handler = StreamlitHandler(log_area)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

# Function to generate markdown content using Google AI Studio API
def generate_markdown(api_key, prompt, markdown_content, progress_bar, logger):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        logger.info("Initiating Gemini API call.")
        logger.info("API configuration done")
        response = model.generate_content(prompt + "\n\n" + markdown_content,
                                            generation_config=genai.GenerationConfig(
                                             # max_output_tokens = 2048
                                             ),
                                            stream=False,
                                            timeout=60
                                           )
        logger.info("Gemini API call completed.")
        progress_bar.progress(100)
        return response.text
    except Exception as e:
        logger.error(f"An error occurred during Gemini API call: {e}")
        return f"An error occurred: {e}"

# Function to split markdown content into multiple files if too long
def split_markdown(markdown_content, max_length=10000):
    parts = []
    while markdown_content:
        if len(markdown_content) <= max_length:
            parts.append(markdown_content)
            break
        else:
            split_index = markdown_content.rfind('\n\n', 0, max_length)
            if split_index == -1:
                split_index = max_length
            parts.append(markdown_content[:split_index])
            markdown_content = markdown_content[split_index:]
    return parts

def create_download_buttons(markdown_parts):
    if len(markdown_parts) == 1:
        st.download_button(
            label="Download Markdown File",
            data=markdown_parts[0],
            file_name="edited_document.md",
            mime="text/markdown"
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, part in enumerate(markdown_parts):
                zip_file.writestr(f"edited_document_{i + 1}.md", part)
        st.download_button(
            label="Download All Markdown Files (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="edited_documents.zip",
            mime="application/zip"
        )

def display_markdown_parts(markdown_parts):
    for i, part in enumerate(markdown_parts):
        st.markdown(f"**Part {i+1}:**")
        st.markdown(part)

def main():
    st.title("Markdown Editor with Google AI Studio")
    log_area = st.empty() # 创建一个空的占位符，用于日志显示
    logger = create_logger(log_area)

    # API Key Input, 默认值可以从环境变量中获取, 如果没有则为空字符串
    default_api_key = os.getenv("DEFAULT_API_KEY", "")
    api_key = st.text_input("Enter your Google AI Studio API Key", type="password", value=default_api_key)


    # File upload
    uploaded_file = st.file_uploader("Upload Markdown file", type=["md"])

    # Prompt input
    default_prompt = """你是专业又善于教学分享的空间分析师，请编辑下方教案内容（markdown 格式），以方便学生理解。

要求：
1. 所有🚩出现的地方，都是需要修改的。具体修改方式：
 - 如果 🚩 出现在 markdown 正文中，请按照 “🚩：”后面的文字补充内容，篇幅 1-3 段落，新增 1-3 段落；
 - 如果 🚩针对的是输出解读，可以提示你不能按要求完成解读的原因；
 - 如果 🚩 出现在代码注释中，请按照 🚩 后方的提示，后缀注释。

2. 没有🚩的已有内容，不作任何修改；
3. 修改后，生成的内容以为 markdown 格式提供、以便下载；
4. 仔细检查生成的内容，避免任何遗漏；
4. 参考我提供给你的 markdown 代码格式，所有 python 代码应该包裹在 【```python ```】里面；
5. 如果生成内容过长，请分作 2-3 份 markdown 文件提供，以免被阶段。
6. 分作多份markdown文件提供时，下一份输出文件总是从上一份输出文件的最后一段 markdown 段落开始。"""
    prompt = st.text_area("Enter your prompt", value=default_prompt)

    if uploaded_file is not None and api_key:
        markdown_content = uploaded_file.read().decode("utf-8")
        if st.button("Generate Edited Markdown"):
            progress_bar = st.progress(0)
            with st.spinner("Generating edited markdown..."):
                generated_markdown = generate_markdown(api_key, prompt, markdown_content, progress_bar, logger)
                if "An error occurred:" in generated_markdown:
                   st.error(generated_markdown)
                   logger.error(f"Error during markdown generation: {generated_markdown}")
                else:
                    logger.info("Markdown generation successful.")
                    markdown_parts = split_markdown(generated_markdown)
                    create_download_buttons(markdown_parts)
                    display_markdown_parts(markdown_parts)
    elif uploaded_file is None:
        st.warning("Please upload a Markdown file.")

if __name__ == "__main__":
    main()