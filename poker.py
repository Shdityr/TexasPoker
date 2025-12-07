import streamlit as st
from deuces.card import Card
from deuces.deck import Deck
from deuces.evaluator import Evaluator
import random

## --- 1. 牌面常量和转换函数 ---

RANKS = '23456789TJQKA'
SUITS = 'shdc' # s=Spades, h=Hearts, d=Diamonds, c=Clubs

def create_all_cards():
    """生成 deuces 格式的 52 张牌字符串列表 ('Ah', 'Ks', ...)"""
    all_cards_str = []
    for rank in RANKS:
        for suit in SUITS:
            all_cards_str.append(rank + suit)
    return all_cards_str

ALL_CARDS_STR = create_all_cards()

def format_card_to_emoji(card_str):
    """将 'As' 格式的牌转换为图形化的 'A♠️' 格式"""
    if not card_str or len(card_str) != 2:
        return card_str
        
    rank = card_str[0].upper()
    suit_char = card_str[1].lower()
    
    suit_map = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
    
    display_rank = rank_map.get(rank, rank)
    display_suit = suit_map.get(suit_char, '')
    
    return f"{display_rank}{display_suit}"

# 生成用于 Streamlit 下拉框的图形化列表
EMOJI_CARDS = [format_card_to_emoji(c) for c in ALL_CARDS_STR]

def convert_emoji_to_deuces_int(emoji_card):
    """将 'A♥️' 格式的牌转换为 deuces 库可用的整数表示"""
    try:
        # 找到 emoji 牌在图形化列表中的索引
        index = EMOJI_CARDS.index(emoji_card)
        # 使用相同的索引获取 deuces 字符串 ('Ah')
        deuces_str = ALL_CARDS_STR[index]
        # 转换为 deuces 整数
        return Card.new(deuces_str)
    except ValueError:
        return None

# --- 新增：精确计算函数 ---
def enumerate_equity(player_hand_int, board_int):
    """
    当公共牌数量为 4 或 5 时，通过遍历所有剩余有效组合来计算精确胜率。
    """
    evaluator = Evaluator()
    wins = 0
    ties = 0
    total_sims = 0

    # 预先生成所有 52 张牌的 deuces 整数列表
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    known_cards = player_hand_int + board_int
    unknown_pool = [c for c in full_deck_int if c not in known_cards]

    num_board = len(board_int)
    
    # 确定还需要抽取多少张牌 (2 张对手牌 + 0 或 1 张公共牌)
    needed_for_opp = 2
    needed_for_board = 5 - num_board
    
    needed_total = needed_for_opp + needed_for_board
    
    # 遍历所有可能的组合
    # combinations(iterable, r) 返回 iterable 中所有长度为 r 的子序列
    for drawn_cards in combinations(unknown_pool, needed_total):
        
        opponent_hand = list(drawn_cards[:needed_for_opp])
        remaining_board = list(drawn_cards[needed_for_opp:])
        final_board = board_int + remaining_board
        
        # 评估牌型
        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        # 比较胜负
        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1
        
        total_sims += 1
        
    if total_sims == 0:
        return 0.0, 0
    
    equity = (wins + 0.5 * ties) / total_sims
    return equity, total_sims

## --- 2. 蒙特卡洛胜率计算函数 ---
import streamlit as st
from deuces.card import Card
from deuces.evaluator import Evaluator
import random
from itertools import combinations

# 假设 ALL_CARDS_STR 在文件顶部已定义

# --- 新增：精确计算函数 ---
def enumerate_equity(player_hand_int, board_int):
    """
    当公共牌数量为 4 或 5 时，通过遍历所有剩余有效组合来计算精确胜率。
    """
    evaluator = Evaluator()
    wins = 0
    ties = 0
    total_sims = 0

    # 预先生成所有 52 张牌的 deuces 整数列表
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    known_cards = player_hand_int + board_int
    unknown_pool = [c for c in full_deck_int if c not in known_cards]

    num_board = len(board_int)
    
    # 确定还需要抽取多少张牌 (2 张对手牌 + 0 或 1 张公共牌)
    needed_for_opp = 2
    needed_for_board = 5 - num_board
    
    needed_total = needed_for_opp + needed_for_board
    
    # 遍历所有可能的组合
    # combinations(iterable, r) 返回 iterable 中所有长度为 r 的子序列
    for drawn_cards in combinations(unknown_pool, needed_total):
        
        opponent_hand = list(drawn_cards[:needed_for_opp])
        remaining_board = list(drawn_cards[needed_for_opp:])
        final_board = board_int + remaining_board
        
        # 评估牌型
        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        # 比较胜负
        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1
        
        total_sims += 1
        
    if total_sims == 0:
        return 0.0, 0
    
    equity = (wins + 0.5 * ties) / total_sims
    return equity, total_sims


# --- 修改后的主计算函数 ---
@st.cache_data
def calculate_equity(player_hand_int, board_int, simulations=10000):
    
    if len(player_hand_int) != 2:
        return 0.0, "N/A" # 返回胜率和计算类型

    num_board = len(board_int)
    
    # 1. 切换判断逻辑：如果公共牌为 4 或 5 张，使用精确计算
    if num_board >= 4:
        equity, total_sims = enumerate_equity(player_hand_int, board_int)
        return equity, f"精确计算 ({total_sims} 次遍历)"

    # 2. 否则，使用蒙特卡洛模拟
    evaluator = Evaluator()
    wins = 0
    ties = 0
    
    # 预先生成所有 52 张牌的 deuces 整数列表
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 

    for _ in range(simulations):
        known_cards = player_hand_int + board_int
        unknown_pool = [c for c in full_deck_int if c not in known_cards]
        
        needed_for_opp = 2
        needed_for_board = 5 - num_board
        needed_total = needed_for_opp + needed_for_board
        
        if len(unknown_pool) < needed_total:
            continue 

        # 随机抽取所需的牌
        drawn_cards = random.sample(unknown_pool, needed_total)
        
        opponent_hand = drawn_cards[:needed_for_opp]
        remaining_board = drawn_cards[needed_for_opp:]
        
        final_board = board_int + remaining_board

        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1

    equity = (wins + 0.5 * ties) / simulations
    return equity, f"蒙特卡洛 ({simulations} 次模拟)"   

## --- 3. Streamlit 应用界面 ---

st.set_page_config(page_title="♠️ Heads-Up 德州扑克胜率计算器", layout="centered")
st.title("♠️ Heads-Up 德州扑克胜率计算器")
st.markdown("---")

# 初始化 Session State 以确保选择不重复
if 'available_cards' not in st.session_state:
    st.session_state.available_cards = EMOJI_CARDS.copy()

def update_available_cards(selected_cards):
    """根据已选的牌更新可选列表"""
    # 将所有已选牌从完整的 EMOJI_CARDS 列表中排除
    st.session_state.available_cards = [c for c in EMOJI_CARDS if c not in selected_cards]

# ----------------------------------------------------
# 1. 您的手牌 (Hole Cards)
# ----------------------------------------------------
st.header("1. 您的手牌 (Hole Cards)")

# 由于 Streamlit 的 selectbox 刷新机制，这里需要手动处理依赖关系
all_selected_cards = []

col1, col2 = st.columns(2)
with col1:
    h1_emoji = st.selectbox("第一张牌", EMOJI_CARDS, key="h1_emoji")
    all_selected_cards.append(h1_emoji)
    
# 动态更新第二张牌的选项，排除第一张牌
h2_options = [c for c in EMOJI_CARDS if c != h1_emoji]
with col2:
    h2_emoji = st.selectbox("第二张牌", h2_options, key="h2_emoji")
    all_selected_cards.append(h2_emoji)

# ----------------------------------------------------
# 2. 公共牌 (Board)
# ----------------------------------------------------
st.header("2. 公共牌 (Board)")

# 动态更新所有公共牌的选项，排除已选的手牌
board_options = [c for c in EMOJI_CARDS if c not in [h1_emoji, h2_emoji]]

# 翻牌 (Flop) - 使用 multiselect 更符合实际操作
flop_emoji = st.multiselect("翻牌 (Flop, 0或3张)", board_options, max_selections=3, key="flop_emoji")
all_selected_cards.extend(flop_emoji)

# 动态更新转牌的选项
turn_options = [c for c in board_options if c not in flop_emoji]
turn_emoji = st.selectbox("转牌 (Turn, 0或1张)", [""] + turn_options, key="turn_emoji")
if turn_emoji:
    all_selected_cards.append(turn_emoji)

# 动态更新河牌的选项
river_options = [c for c in turn_options if c != turn_emoji]
river_emoji = st.selectbox("河牌 (River, 0或1张)", [""] + river_options, key="river_emoji")
if river_emoji:
    all_selected_cards.append(river_emoji)


# ----------------------------------------------------
# 3. 结果计算
# ----------------------------------------------------
st.markdown("---")
if st.button("🚀 计算当前胜率"):
    
    # 检查手牌是否重复 (虽然通过下拉框控制，但最好做最终检查)
    if h1_emoji == h2_emoji:
        st.error("⚠️ 您的两张手牌不能相同。")
    else:
        with st.spinner('正在运行蒙特卡洛模拟...这可能需要几秒钟'):
            
            # 将所有选中的 Emoji 牌转换为 deuces 整数
            player_hand_int = [
                convert_emoji_to_deuces_int(h1_emoji), 
                convert_emoji_to_deuces_int(h2_emoji)
            ]
            
            board_int = []
            for emoji in flop_emoji:
                board_int.append(convert_emoji_to_deuces_int(emoji))
            if turn_emoji:
                board_int.append(convert_emoji_to_deuces_int(turn_emoji))
            if river_emoji:
                board_int.append(convert_emoji_to_deuces_int(river_emoji))
            
            
                
            if len(player_hand_int) == 2:
                with st.spinner('正在计算胜率...'):
                    # 调用更新后的函数
                    equity, calc_type = calculate_equity(player_hand_int, board_int, simulations=10000)
                    
                    st.success("✅ **计算完成！**")
                    st.markdown(f"## 您的当前胜率是: **{equity * 100:.2f}%**")
                    
                    st.info(f"计算类型：{calc_type}。")
            else:
                st.error("请选择您的两张手牌。")