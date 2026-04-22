import io
import json
from collections import defaultdict

import pandas as pd
import streamlit as st

# 规范化导入方式
from app.types import (
    AttackTemplate,
    Difficulty,
    Attack,
    AttackSequence,
    DefenseAllocation,
    AttackAllocation
)
from app.st_helper import (
    df_to_attack_template_conditions,
    get_all_available_branch_cond_strs,
    df_to_attack_template_branches,
    df_to_attack_plan
)

# ==========================================
# 常量定义 (避免代码中到处都是硬编码的字符串)
# ==========================================
COL_TEMPLATE = "模板"
COL_ALLOCATION = "分配"
COL_DIFFICULTY = "难度"
COL_CONDITION = "情况"
COL_DAMAGE = "伤害"
COL_EVADE_DIFF = "回避难度"
COL_ATMOSPHERE = "气氛"
COL_NOTE = "备注"


# ==========================================
# 状态初始化
# ==========================================
def init_session_state():
    """初始化 Streamlit Session State"""
    if "attack_templates" not in st.session_state:
        # 存储模板的 DataFrame 原数据
        st.session_state.attack_templates = {}

    if "attack_plan" not in st.session_state:
        st.session_state.attack_plan = pd.DataFrame(dtype=str, columns=[COL_TEMPLATE])

    if "attack_allocation" not in st.session_state:
        st.session_state.attack_allocation = pd.DataFrame([], dtype=pd.Int8Dtype, columns=[COL_ALLOCATION])


# ==========================================
# 侧边栏：导入与导出模块
# ==========================================
def render_sidebar(raw_dataframe_templates: dict):
    """渲染侧边栏，处理模板的导入与导出"""
    with st.sidebar:
        st.header("数据管理")

        # 导出功能
        if st.checkbox("导出攻击模板"):
            # 将 DataFrame 转换为 dict 以便 JSON 序列化
            json_data = {
                k: [
                    cond_df.to_dict(orient='records'),
                    branch_df.to_dict(orient='records')
                ]
                for k, (cond_df, branch_df) in raw_dataframe_templates.items()
            }
            json_string = json.dumps(json_data, ensure_ascii=False)
            st.download_button(
                label="下载模板 JSON",
                data=json_string,
                file_name="attack_templates.json",
                mime="application/json"
            )
            st.text_area("JSON 预览", value=json_string, height=200)

        st.divider()

        # 导入功能
        if st.checkbox("导入攻击模板"):
            text = st.text_area(label="粘贴 JSON 数据到这里")
            if st.button("确定导入"):
                try:
                    raw_data = json.loads(text)
                    loaded_dict = {
                        k: (pd.DataFrame(v[0]), pd.DataFrame(v[1]))
                        for k, v in raw_data.items()
                    }
                    st.session_state.attack_templates = loaded_dict
                    st.success("导入成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"导入失败: {e}")


# ==========================================
# 主界面：模板编辑区 (左栏)
# ==========================================
def render_template_editor() -> tuple[dict[str, AttackTemplate], dict[str, tuple[pd.DataFrame, pd.DataFrame]]]:
    """渲染模板编辑器，返回解析后的模板对象和原始DataFrame数据"""
    st.subheader("攻击模板配置")

    # 新增模板
    with st.form("add_template_form"):
        col_input, col_btn = st.columns([3, 1])
        added_template_name = col_input.text_input("新增模板名称", label_visibility="collapsed",
                                                   placeholder="输入模板名称...")
        submitted = col_btn.form_submit_button("添加模板")

        if submitted:
            if not added_template_name.strip():
                st.error("请输入有效的模板名称")
            elif added_template_name in st.session_state.attack_templates:
                st.warning("模板名称已存在")
            else:
                # 初始化空数据
                st.session_state.attack_templates[added_template_name] = (
                    pd.DataFrame({COL_DIFFICULTY: []}, dtype=str),
                    pd.DataFrame({COL_CONDITION: [], COL_DAMAGE: [], COL_EVADE_DIFF: [], COL_ATMOSPHERE: [], COL_NOTE:[]}, dtype=str),
                )

    # 解析后的数据容器
    parsed_templates: dict[str, AttackTemplate] = {}
    raw_dataframe_templates: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}

    keys = list(st.session_state.attack_templates.keys())
    if keys:
        tabs = st.tabs(keys)
        for i, tab in enumerate(tabs):
            with tab:
                key = keys[i]
                df_cond, df_branch = st.session_state.attack_templates[key]

                st.caption("1. 触发难度配置")
                edited_conditions = st.data_editor(df_cond, num_rows="dynamic", key=f"cond_{key}")
                parsed_conditions = df_to_attack_template_conditions(edited_conditions)

                if not parsed_conditions:
                    st.warning("未填入任何触发难度 或 格式不正确")


                cond_strs = get_all_available_branch_cond_strs(parsed_conditions)

                st.caption("2. 分支情况配置")
                branches_col_config = {
                    COL_CONDITION: st.column_config.SelectboxColumn(
                        options=cond_strs,
                        pinned=True,
                        required=True
                    ),
                    COL_ATMOSPHERE: st.column_config.SelectboxColumn(
                        options=["近战","远程","术","无"],
                        default="近战"
                    )
                }
                edited_branches = st.data_editor(
                    df_branch,
                    num_rows="dynamic",
                    column_config=branches_col_config,
                    key=f"branch_{key}"
                )

                for i in range(0,3):
                    parsed_branches = df_to_attack_template_branches(edited_branches,i)
                    if parsed_branches:
                        parsed_templates[key+":"+str(i)] = AttackTemplate(branches=parsed_branches, conditions=parsed_conditions)

                parsed_branches = df_to_attack_template_branches(edited_branches,0)
                if not parsed_branches:
                    st.warning("分支格式可能不正确")

                # 保存状态
                parsed_templates[key] = AttackTemplate(branches=parsed_branches, conditions=parsed_conditions)
                raw_dataframe_templates[key] = (edited_conditions, edited_branches)

    return parsed_templates, raw_dataframe_templates


def render_trend_chart(attack_plan, current_atk: int, current_def: int):
    """绘制伤害随骰子数量变化的趋势折线图"""
    st.write("#### 📊 伤害趋势分析")

    # 使用折叠面板，保持界面整洁
    with st.expander("展开/折叠趋势图配置", expanded=False):
        st.info(f"**当前基准设置**：当改变一侧骰数时，另一侧会固定为当前值（攻击={current_atk}, 回避={current_def}）")

        # 1. 设置配置项
        col_radio, col_slider = st.columns([1, 1])
        trend_var = col_radio.radio(
            "选择自变量 (X轴)",
            options=["变化攻击骰数", "变化回避骰数"],
            horizontal=True
        )

        # 让用户选择要计算的骰数范围
        x_min, x_max = col_slider.slider(
            "计算范围",
            min_value=0, max_value=30, value=(1, 20)
        )

        # 2. 计算与绘制逻辑
        if st.button("📈 开始绘制趋势图", type="primary"):
            if not attack_plan:
                st.error("攻击计划为空！")
                return

            # 初始化进度条和状态文本
            progress_bar = st.progress(0)
            status_text = st.empty()

            chart_data = []
            total_steps = x_max - x_min + 1

            # 遍历计算
            for i, x in enumerate(range(x_min, x_max + 1)):
                status_text.caption(f"正在计算: 骰子数 {x} ...")

                # 根据选择变化不同的变量
                if "攻击" in trend_var:
                    # 攻击变，回避固定
                    _, expected_dmg = attack_plan.best_allocation(x, current_def)
                else:
                    # 回避变，攻击固定
                    _, expected_dmg = attack_plan.best_allocation(current_atk, x)

                chart_data.append({
                    "骰子数量": x,
                    "期望伤害": expected_dmg
                })

                # 更新进度条
                progress_bar.progress((i + 1) / total_steps)

            # 计算完成，清空进度提示
            status_text.empty()
            progress_bar.empty()

            # 3. 构造 DataFrame 并绘制图表
            df_chart = pd.DataFrame(chart_data)
            df_chart.set_index("骰子数量", inplace=True)  # 将骰子数量设为 X 轴

            st.success("计算完成！")
            # 使用内置的 line_chart 绘制，y轴指定为我们计算出的伤害
            st.line_chart(df_chart, y="期望伤害")

            # (可选) 展示详细数据表格，方便用户查阅具体数值
            with st.popover("查看具体数值"):
                st.dataframe(df_chart.T)  # 转置一下横向显示更方便


# ==========================================
# 主界面：战斗推演区 (右栏)
# ==========================================
def render_combat_simulator(parsed_templates: dict[str, AttackTemplate]):
    """渲染战斗模拟和期望计算器"""
    st.subheader("攻击计划推演")

    col_dice1, col_dice2 = st.columns(2)
    num_attack_dice = col_dice1.number_input("攻击骰数", min_value=0, max_value=30, value=10)
    num_defense_dice = col_dice2.number_input("回避骰数", min_value=0, max_value=30, value=8)

    atmosphere = st.number_input("气氛", min_value=0, max_value=2, value=0)

    st.write("#### 制定攻击计划")

    if not parsed_templates:
        st.info("请先在左侧创建并完善攻击模板")
        return

    plan_col_config = {
        COL_TEMPLATE: st.column_config.SelectboxColumn(
            options=[key for key in parsed_templates.keys() if not key.endswith(":0") and not key.endswith(":1") and not key.endswith(":2")],
            pinned=True,
            required=True
        )
    }

    edited_sequence = st.data_editor(st.session_state.attack_plan, num_rows="dynamic", column_config=plan_col_config)
    attack_plan = df_to_attack_plan(edited_sequence, parsed_templates, atmosphere)

    if not attack_plan:
        st.error("不正确的格式或引用")
        return

    # ==== 计算逻辑区 ====
    st.divider()

    if st.button("1. 计算最佳分配", type="primary"):
        best_alloc, best_damage = attack_plan.best_allocation(num_attack_dice, num_defense_dice)

        new_alloc_df = pd.DataFrame({
            COL_ALLOCATION: best_alloc.allocation
        }).astype(pd.Int8Dtype())  # 保持类型一致

        st.session_state.attack_allocation = new_alloc_df

        st.success(f"**最佳总期望伤害:** {best_damage:.2f}")
        st.info(f"**最佳攻击分配:** `{best_alloc.allocation}`")

        # 调试缓存信息
        st.caption(f"Cache info: {DefenseAllocation.best_allocation.cache_info()}")

    st.write("#### 详细推演分析")
    edited_allocation = st.data_editor(st.session_state.attack_allocation, num_rows="dynamic")

    if st.button("2. 根据上述分配计算详情"):
        try:
            alloc_array = list(map(int, list(edited_allocation[COL_ALLOCATION])))
            total_res = sum(alloc_array)
            attack_allocation_obj = AttackAllocation(allocation=alloc_array, total_resource=total_res)

            st.write("当前采用分配:", attack_allocation_obj.allocation)
            expanded_plan = attack_plan.expand(allocation=attack_allocation_obj)

            result_table = []
            for prob, seq in expanded_plan:
                def_alloc, expected_dmg = DefenseAllocation.best_allocation(seq, num_defense_dice)
                weighted_dmg = prob * expected_dmg

                result_table.append({
                    "发生概率": prob,
                    "结果攻击序列": str(seq),
                    "最佳回避分配": str(def_alloc.allocation),
                    "期望伤害": expected_dmg,
                    "加权期望伤害": weighted_dmg
                })

            df_result = pd.DataFrame(result_table)

            # 使用 dataframe 更好的展示并高亮
            st.dataframe(
                df_result.style.format({"发生概率": "{:.2%}", "期望伤害": "{:.2f}", "加权期望伤害": "{:.3f}"}),
                width="stretch"
            )

            total_expected_dmg = df_result["加权期望伤害"].sum()
            st.metric("总期望伤害 (Total Expected Damage)", f"{total_expected_dmg:.3f}")

        except Exception as e:
            st.error(f"计算失败，请检查分配格式是否正确: {e}")

        # 在最底部的独立位置加入折线图功能
    st.divider()  # 加一条分割线
    render_trend_chart(attack_plan, num_attack_dice, num_defense_dice)

# ==========================================
# 页面主入口
# ==========================================
def main():
    st.set_page_config(layout="wide", page_title="Combat Simulator")
    init_session_state()

    # 布局分栏
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        parsed_templates, raw_dataframe_templates = render_template_editor()

    # 侧边栏依赖于左侧解析出的原始DataFrame，所以在左侧渲染后调用
    render_sidebar(raw_dataframe_templates)

    with col_right:
        render_combat_simulator(parsed_templates)

    #st.session_state.attack_templates = raw_dataframe_templates

if __name__ == "__main__":
    main()