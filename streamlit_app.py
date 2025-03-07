import streamlit as st
import requests
import json
from websockets.sync.client import connect
import time
import sqlite3

# 界面配置
st.set_page_config(
    page_title="AI小说工坊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': "mailto:your@email.com",
    }
)

# 自定义CSS样式
st.markdown("""
<style>
.stTextInput>div>div>input {
    font-size: 16px;
    padding: 12px;
}
.stButton>button {
    background-color: #4CAF50;
    color: white;
    padding: 10px 24px;
    border-radius: 5px;
}
.stProgress > div > div > div > div {
    background-color: #4CAF50;
}
</style>
""", unsafe_allow_html=True)

# 初始化数据库连接
conn = sqlite3.connect('stories.db', check_same_thread=False)

def main():
    with st.sidebar:
        st.header("⚙️ 创作设置")
        genre = st.selectbox("故事类型", ["武侠", "奇幻", "悬疑", "言情"], index=0)
        creativity = st.slider("创意强度", 0.5, 1.0, 0.8, 0.05)
        st.divider()
        st.markdown("### 历史作品")
        stories = conn.execute("SELECT title FROM stories").fetchall()
        selected_story = st.selectbox("选择已有作品", [s[0] for s in stories] if stories else ["无"])
    
    st.title("📖 零成本AI小说创作系统")
    
    # 大綱生成區
    if "outline" not in st.session_state:
        with st.form("outline_form"):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("小说标题", placeholder="请输入小说标题...")
            with col2:
                characters = st.multiselect("主要角色", 
                    ["少年主角", "神秘导师", "宿敌反派", "红颜知己", "搞笑搭档"],
                    default=["少年主角", "宿敌反派"])
            
            if st.form_submit_button("生成大纲", type="primary"):
                with st.spinner("正在构思精采大纲..."):
                    response = requests.post(
                        "http://localhost:8000/generate_outline",
                        json={
                            "title": title,
                            "genre": genre,
                            "characters": characters,
                            "max_length": 800
                        }
                    )
                    if response.status_code == 200:
                        st.session_state.outline = response.json()["outline"]
                    else:
                        st.error("大纲生成失败，请检查后端服务")

    # 章節生成區
    if "outline" in st.session_state:
        st.markdown("## 大纲预览")
        with st.expander("点击查看完整大纲"):
            st.markdown(st.session_state.outline)
        
        st.divider()
        st.subheader("章节创作")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            chapter_num = st.number_input("选择章节", 1, 10, 1)
            previous_summary = st.text_area("前情提要", height=150,
                                          placeholder="输入前几章的重要剧情...")
            generate_btn = st.button(f"生成第 {chapter_num} 章", type="secondary")
        
        with col2:
            if generate_btn:
                progress_bar = st.progress(0)
                status_text = st.empty()
                chapter_content = ""
                
                with connect("ws://localhost:8000/write_chapter") as ws:
                    ws.send(json.dumps({
                        "chapter": chapter_num,
                        "outline": st.session_state.outline,
                        "genre": genre,
                        "previous_summary": previous_summary
                    }))
                    
                    placeholder = st.empty()
                    for i in range(100):
                        try:
                            chunk = ws.recv()
                            chapter_content += chunk
                            placeholder.markdown(f"**第 {chapter_num} 章内容**\n\n" + 
                                                chapter_content + "▌")
                            progress_bar.progress((i+1)/100)
                        except:
                            break
                    
                    progress_bar.empty()
                    st.session_state[f"chapter_{chapter_num}"] = chapter_content