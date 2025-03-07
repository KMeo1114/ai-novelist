from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import sqlite3
from ctransformers import AutoModelForCausalLM
import time
import sys
import io

# 解决中文编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

app = FastAPI()

# 加载本地模型 (重要：模型需提前下载到models目录)
model = AutoModelForCausalLM.from_pretrained(
    "models/uer-gpt2",
    model_type="gpt2",
    lib="avx2",
    threads=4,
    context_length=512
)

class StoryRequest(BaseModel):
    title: str
    genre: str
    characters: list[str]
    max_length: int = 500

# 初始化数据库
conn = sqlite3.connect('stories.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS stories
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              title TEXT, 
              outline TEXT, 
              chapters TEXT)''')
conn.commit()

# 专业级提示词模板
OUTLINE_PROMPT = """
你是一位专业小说家，请为《{title}》创作包含10章的大纲：
类型：{genre}
主要角色：{characters}

要求：
1. 使用三幕剧结构（铺垫-冲突-解决）
2. 每章结尾留下悬念
3. 第3章设置首次重大转折
4. 第7章出现核心危机

输出格式：
## 大纲
### 第一章 [章节标题]
- 核心事件：...
- 角色发展：...
"""

CHAPTER_PROMPT = """
根据以下大纲续写第{chapter_num}章内容：
{outline}

创作要求：
- 保持{genre}风格
- 包含至少2个场景描写
- 对话占比30%以上
- 末尾留下悬念

前情提要：{previous_summary}

正文：
"""

@app.post("/generate_outline")
def generate_outline(request: StoryRequest):
    prompt = OUTLINE_PROMPT.format(
        title=request.title,
        genre=request.genre,
        characters="、".join(request.characters)
    )
    
    # 生成优化配置
    outline = model(
        prompt,
        max_length=request.max_length,
        temperature=0.85,
        repetition_penalty=1.2
    )
    
    # 保存到数据库
    c.execute('INSERT INTO stories (title, outline) VALUES (?, ?)',
             (request.title, outline))
    conn.commit()
    
    return {"outline": outline}

@app.websocket("/write_chapter")
async def write_chapter(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        
        prompt = CHAPTER_PROMPT.format(
            chapter_num=data['chapter'],
            outline=data['outline'],
            genre=data['genre'],
            previous_summary=data.get('previous_summary', "")
        )
        
        # 流式生成实现
        full_text = ""
        for text in model.generate(
            prompt,
            stream=True,
            temperature=0.9,
            top_p=0.95,
            max_new_tokens=300
        ):
            full_text += text
            await websocket.send_text(text)
            time.sleep(0.05)  # 控制输出速度
            
    except Exception as e:
        print(f"生成错误: {str(e)}")