# 🚀 ALEM SMM PRO: Автономный AI Арт-Директор

**Decentrathon 5 | Hackathon MVP**

Система, которая автоматизирует весь цикл SMM-продакшена: от идеи или скриншота-референса до готового, сверстанного журнального поста (Carousel, Single, Story) и его автоматической публикации в Instagram. Построено на базе мультимодальных моделей **alem.plus**, кастомного рендеринга на Python и Meta Graph API.

---

## 🎮 Live Demo & Результаты работы

В целях безопасности API-ключи скрыты, но система развернута на сервере и полностью функционирует.

📹 **Примечание к демо-видео:** Процесс параллельной генерации изображений и выгрузки через Meta API занимает около 1-2 минут реального времени. Если видео кажется долгим, **вы можете сразу посмотреть готовые результаты работы нашего ИИ в Instagram:**

👉 **[Смотреть готовые посты в Instagram (@mono.observer.ai)](https://www.instagram.com/mono.observer.ai?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw==)**

Вы также можете протестировать систему сами:
* **Telegram Bot (Интерфейс):** [@mono_control_for_instagram_bot](https://t.me/mono_control_for_instagram_bot)
* *Отправьте `/start` -> Выберите формат -> Напишите тему, отправьте голосовое сообщение или скиньте скриншот любого поста конкурента.*

> ⚠️ **ВАЖНОЕ ЗАМЕЧАНИЕ (META API TOKEN):**
> Токены доступа Meta Graph API имеют ограниченный срок действия. Если во время тестирования бота на этапе публикации в Instagram вы получите ошибку (например, `Meta Error` или проблему с `id`), это означает, что срок жизни ключа истек. 
> **Пожалуйста, напишите мне в Telegram: [@yernur_dev](https://t.me/yernur_dev) — я обновлю API-ключ на сервере за 1 минуту!**

---

## 🏗 Архитектура системы (Data Flow)

```mermaid
graph TD
classDef ui fill:#1E3A8A,stroke:#3B82F6,stroke-width:2px,color:#fff;
classDef ai fill:#4C1D95,stroke:#8B5CF6,stroke-width:2px,color:#fff;
classDef back fill:#064E3B,stroke:#10B981,stroke-width:2px,color:#fff;
classDef api fill:#78350F,stroke:#F59E0B,stroke-width:2px,color:#fff;

UI[📱 Telegram Bot <br> aiogram / 3 routing branches]:::ui

subgraph Input Processors
    T[✍️ Text Input]:::ui
    V[🎙️ Voice Input]:::ui
    I[🖼️ Image Input]:::ui
    STT[🔊 Speech-to-Text kk <br> alem.plus]:::ai
    OCR[👁️ Qwen3 Vision OCR <br> alem.plus]:::ai
end

subgraph Core Brain
    PLAN[🧠 AI Content Planner <br> Qwen3 LLM: JSON Plan]:::ai
end

subgraph Parallel Processing
    CRITIC[⚖️ AI-Critic <br> Qwen3: Virality Score 1-10]:::ai
    GEN[🎨 Image Generation <br> Qwen T2I: 1-4 images async]:::ai
end

subgraph Dynamic Assembler
    PILLOW[⚙️ Python Pillow Renderer <br> Layout assembly & Adaptive text]:::back
end

subgraph Output
    META[🌐 Meta Graph API <br> Carousel Container -> Instagram Business]:::api
end

UI --> T & V & I
V --> STT
I --> OCR
T --> PLAN
STT --> PLAN
OCR --> PLAN

PLAN --> CRITIC & GEN
CRITIC --> PILLOW
GEN --> PILLOW
PILLOW --> META
