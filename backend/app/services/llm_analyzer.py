from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import os
import uuid
import io
import json
import ast
from contextlib import redirect_stdout
from pathlib import Path
from typing import Optional
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

load_dotenv()

client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)


def _validate_code(code: str) -> None:
    tree = ast.parse(code)
    banned_modules = {"os", "sys", "subprocess", "pathlib", "socket", "shutil"}
    banned_names = {"open", "eval", "exec", "compile", "__import__", "input"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod_name = ""
            if isinstance(node, ast.Import):
                mod_name = node.names[0].name.split(".")[0]
            else:
                mod_name = (node.module or "").split(".")[0]
            if mod_name in banned_modules:
                raise ValueError(f"Импорт модуля '{mod_name}' запрещен")

        if isinstance(node, ast.Name) and node.id in banned_names:
            raise ValueError(f"Использование '{node.id}' запрещено")


def _execute_python_tool(code: str, df: pd.DataFrame, charts_dir: Path) -> dict:
    _validate_code(code)
    charts_dir.mkdir(parents=True, exist_ok=True)
    created_charts: list[str] = []

    def save_chart(name: Optional[str] = None) -> str:
        chart_name = name or f"{uuid.uuid4().hex[:10]}.png"
        chart_path = charts_dir / chart_name
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()
        rel_path = f"charts/{chart_name}"
        created_charts.append(rel_path)
        return rel_path

    safe_builtins = {
        "len": len,
        "min": min,
        "max": max,
        "sum": sum,
        "sorted": sorted,
        "round": round,
        "range": range,
        "enumerate": enumerate,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "abs": abs,
        "print": print,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
    }

    execution_scope = {
        "__builtins__": safe_builtins,
        "df": df.copy(),
        "pd": pd,
        "np": np,
        "plt": plt,
        "save_chart": save_chart,
        "result": None,
    }

    stdout_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer):
        # Use one shared scope so df/pd/np are always visible
        # across statements, comprehensions and nested blocks.
        exec(code, execution_scope, execution_scope)

    result_value = execution_scope.get("result")
    used_fallback_result = result_value is None
    if used_fallback_result:
        # Гарантируем, что инструмент всегда возвращает полезные вычисленные данные.
        result_value = {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": [str(col) for col in df.columns[:50]],
            "numeric_columns": [str(col) for col in df.select_dtypes(include="number").columns],
            "missing_values": {
                str(col): int(val)
                for col, val in df.isnull().sum().to_dict().items()
            },
        }

    return {
        "stdout": stdout_buffer.getvalue(),
        "result": result_value,
        "charts": created_charts,
        "result_was_fallback": used_fallback_result,
    }


def _generate_fallback_chart(df: pd.DataFrame, charts_dir: Path) -> list[str]:
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_name = f"{uuid.uuid4().hex[:10]}_fallback.png"
    chart_path = charts_dir / chart_name

    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        first_col = numeric_df.columns[0]
        plt.figure(figsize=(10, 6))
        numeric_df[first_col].dropna().hist(bins=30)
        plt.title(f"Распределение: {first_col}")
        plt.xlabel(first_col)
        plt.ylabel("Частота")
    else:
        plt.figure(figsize=(8, 4))
        plt.text(
            0.5,
            0.5,
            "Авто-график: недостаточно\nчисловых данных для гистограммы",
            ha="center",
            va="center",
            fontsize=12,
        )
        plt.axis("off")

    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()
    return [f"charts/{chart_name}"]


def analyze_with_llm(
    df: pd.DataFrame,
    user_prompt: str,
    mode: str = "report"
) -> tuple[str, list[str]]:
    charts_dir = Path(__file__).resolve().parents[1] / "static" / "charts"
    charts_from_tools: list[str] = []
    last_tool_result: Optional[dict] = None
    tool_schema = [
        {
            "type": "function",
            "function": {
                "name": "python_interpreter",
                "description": (
                    "Выполняет Python-код для анализа датафрейма df. "
                    "Для построения графиков используй matplotlib и вызов save_chart()."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": (
                                "Python-код. Доступно: df, pd, np, plt, save_chart, result. "
                                "Перед завершением обязательно присвой переменной result "
                                "словарь с численными итогами вычислений. "
                                "Перед обращением к любой колонке обязательно проверяй, "
                                "что она существует в df.columns."
                            ),
                        }
                    },
                    "required": ["code"],
                },
            },
        }
    ]

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "Ты MiMo, экспертный AI-аналитик данных. "
                "ОБЯЗАТЕЛЬНО сначала выполни анализ через python_interpreter, "
                "не делай выводы без вызова инструмента. "
                + (
                    "ОБЯЗАТЕЛЬНО создай минимум 1 график через save_chart(). "
                    if mode == "report"
                    else "Графики создавай только когда это действительно нужно для ответа. "
                )
                + 
                "Всегда отвечай только на русском языке. "
                "Запрещено использовать вымышленные названия колонок. "
                "Работай только с реально существующими колонками из df.columns."
            ),
        },
        {
            "role": "user",
            "content": (
                (
                    "Проведи полный анализ датасета через инструмент python_interpreter. "
                    "Не опирайся на предположения без вычислений.\n\n"
                    "Инструкции пользователя:\n"
                    f"{user_prompt}\n\n"
                    "В финальном markdown-отчете обязательно включи:\n"
                    "- краткое резюме\n"
                    "- важные тренды\n"
                    "- аномалии\n"
                    "- корреляции\n"
                    "- бизнес-инсайты\n"
                    "- рекомендации\n"
                    '- раздел "Варианты запросов для графиков" (минимум 5 пунктов, '
                    "каждый с указанием типа графика).\n"
                )
                if mode == "report"
                else (
                    "Ответь на вопрос по ранее загруженному датасету через "
                    "python_interpreter. Не опирайся на предположения без вычислений.\n\n"
                    f"Вопрос пользователя:\n{user_prompt}\n\n"
                    "Формат ответа:\n"
                    "- короткий ответ по существу\n"
                    "- ключевые расчеты/факты\n"
                    "- выводы и рекомендации по вопросу\n"
                )
            ),
        },
    ]

    final_report = ""
    forced_tool = True
    had_tool_error = False

    for _ in range(8):
        response = client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=messages,
            tools=tool_schema,
            tool_choice="required" if forced_tool else "auto",
            temperature=0.2,
            top_p=0.95,
            max_completion_tokens=3072,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        reasoning_content = getattr(message, "reasoning_content", None)
        assistant_message = {
            "role": "assistant",
            "content": message.content or "",
        }
        if reasoning_content:
            assistant_message["reasoning_content"] = reasoning_content

        if tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ]

            messages.append(assistant_message)
            has_tool_error = False

            for call in tool_calls:
                if call.function.name != "python_interpreter":
                    continue

                payload = json.loads(call.function.arguments or "{}")
                code = payload.get("code", "")

                try:
                    tool_result = _execute_python_tool(code, df, charts_dir)
                except Exception as exc:
                    tool_result = {"error": str(exc), "charts": []}

                last_tool_result = tool_result
                charts_from_tools.extend(tool_result.get("charts", []))
                tool_payload = tool_result
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(
                            tool_payload,
                            ensure_ascii=False,
                            default=str
                        ),
                    }
                )
                if "error" in tool_result:
                    had_tool_error = True
                    messages[-1]["content"] = json.dumps(
                        {
                            "status": "error",
                            "message": (
                                "Инструмент не выполнился. "
                                "Нужно повторить расчет безопасным кодом."
                            ),
                        },
                        ensure_ascii=False,
                    )
                    has_tool_error = True
                    error_text = str(tool_result.get("error", ""))
                    missing_column_note = ""
                    if "KeyError" in error_text or "not in index" in error_text:
                        missing_column_note = (
                            " Ошибка похожа на отсутствие колонки. "
                            f"Доступные колонки: {list(df.columns)[:80]}."
                        )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "В коде инструмента возникла ошибка. "
                                "Исправь Python-код и вызови python_interpreter снова. "
                                "Используй только операции pandas/NumPy на df, "
                                "не применяй методы Series/DataFrame к обычным list. "
                                "Перед использованием каждой колонки проверяй её наличие: "
                                "if 'col' in df.columns. "
                                "Если нужной колонки нет, используй альтернативные существующие."
                                + missing_column_note
                            ),
                        }
                    )

            forced_tool = has_tool_error
            continue

        messages.append(assistant_message)
        final_report = message.content or ""
        if final_report and (charts_from_tools or mode != "report"):
            break

        messages.append(
            {
                "role": "user",
                "content": (
                    "Продолжи: ты еще не выполнил обязательные условия. "
                    + (
                        "Нужно вызвать python_interpreter и создать минимум один график."
                        if mode == "report"
                        else "Нужно вызвать python_interpreter перед финальным ответом."
                    )
                ),
            }
        )
        forced_tool = True

    if not final_report and last_tool_result is not None:
        safe_tool_context: dict
        if "error" in last_tool_result:
            safe_tool_context = {
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
                "column_names": [str(col) for col in df.columns[:50]],
                "missing_values": {
                    str(col): int(val)
                    for col, val in df.isnull().sum().to_dict().items()
                },
            }
        else:
            safe_tool_context = last_tool_result

        fallback_prompt = (
            "Сформируй финальный markdown-отчет ТОЛЬКО на русском языке на основе "
            "результатов вычислений из Python-интерпретатора.\n\n"
            f"Инструкции пользователя:\n{user_prompt}\n\n"
            "Результат вычислений инструмента:\n"
            f"{json.dumps(safe_tool_context, ensure_ascii=False, default=str)[:12000]}\n\n"
            "Включи обязательно:\n"
            + (
                "- краткое резюме\n"
                "- важные тренды\n"
                "- аномалии\n"
                "- корреляции\n"
                "- бизнес-инсайты\n"
                "- рекомендации\n"
                '- раздел "Варианты запросов для графиков" (минимум 5 пунктов, каждый с типом графика).\n'
                if mode == "report"
                else "- ответ по существу вопроса\n- численные подтверждения и вывод\n"
            )
        )
        fallback_response = client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты MiMo, экспертный AI-аналитик данных. "
                        "Отвечай только на русском языке."
                    ),
                },
                {"role": "user", "content": fallback_prompt},
            ],
            temperature=0.2,
            top_p=0.95,
            max_completion_tokens=3072,
        )
        final_report = fallback_response.choices[0].message.content or ""

    if had_tool_error and final_report:
        sanitize_prompt = (
            "Перепиши текст ниже в профессиональный аналитический отчет на русском. "
            "Запрещено упоминать технические ошибки, traceback, NameError, "
            "исключения интерпретатора и внутренние сбои. "
            "Верни только аналитические выводы, допущения и рекомендации.\n\n"
            f"Текст:\n{final_report}"
        )
        sanitize_response = client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты AI-аналитик. Возвращай только чистый отчет без "
                        "внутренних технических деталей."
                    ),
                },
                {"role": "user", "content": sanitize_prompt},
            ],
            temperature=0.2,
            top_p=0.95,
            max_completion_tokens=2048,
        )
        final_report = sanitize_response.choices[0].message.content or final_report

    if not final_report:
        raise RuntimeError("LLM не вернул финальный отчет")

    if mode == "report" and not charts_from_tools:
        charts_from_tools.extend(_generate_fallback_chart(df, charts_dir))

    return final_report, list(dict.fromkeys(charts_from_tools))


def answer_question_with_llm(
    df: pd.DataFrame,
    user_question: str
) -> tuple[str, list[str]]:
    return analyze_with_llm(
        df=df,
        user_prompt=user_question,
        mode="qa"
    )