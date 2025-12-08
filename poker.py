import streamlit as st
from deuces.card import Card
from deuces.deck import Deck
from deuces.evaluator import Evaluator
import random
from itertools import combinations

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

## --- 2. 胜率计算函数 ---

# --- 精确计算函数 (未更改) ---
def enumerate_equity(player_hand_int, board_int):
    """
    当公共牌数量为 4 或 5 时，通过遍历所有剩余有效组合来计算精确胜率。
    """
    evaluator = Evaluator()
    wins = 0
    ties = 0
    total_sims = 0

    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 
    known_cards = player_hand_int + board_int
    unknown_pool = [c for c in full_deck_int if c not in known_cards]

    num_board = len(board_int)
    
    needed_for_opp = 2
    needed_for_board = 5 - num_board
    
    needed_total = needed_for_opp + needed_for_board
    
    for drawn_cards in combinations(unknown_pool, needed_total):
        
        opponent_hand = list(drawn_cards[:needed_for_opp])
        remaining_board = list(drawn_cards[needed_for_opp:])
        final_board = board_int + remaining_board
        
        player_score = evaluator.evaluate(player_hand_int, final_board)
        opponent_score = evaluator.evaluate(opponent_hand, final_board)

        if player_score < opponent_score:
            wins += 1
        elif player_score == opponent_score:
            ties += 1
        
        total_sims += 1
        
    if total_sims == 0:
        return 0.0, 0
    
    equity = (wins + 0.5 * ties) / total_sims
    return equity, total_sims


# --- 主计算函数 (未更改) ---
@st.cache_data
def calculate_equity(player_hand_int, board_int, simulations=10000):
    
    if len(player_hand_int) != 2:
        return 0.0, "N/A" 

    num_board = len(board_int)
    
    if num_board >= 4:
        equity, total_sims = enumerate_equity(player_hand_int, board_int)
        return equity, f"精确计算 ({total_sims} 次遍历)"

    evaluator = Evaluator()
    wins = 0
    ties = 0
    
    full_deck_int = [Card.new(c_str) for c_str in ALL_CARDS_STR] 

    for _ in range(simulations):
        known_cards = player_hand_int + board_int
        unknown_pool = [c for c in full_deck_int if c not in known_cards]
        
        needed_for_opp = 2
        needed_for_board = 5 - num_board
        needed_total = needed_for_opp + needed_for_board
        
        if len(unknown_pool) < needed_total:
            continue 

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

## --- 3. Streamlit 应用界面和随机函数 ---

st.set_page_config(page_title="♠️ Heads-Up 德州扑克胜率计算器", layout="centered")
st.title("♠️ Heads-Up 德州扑克胜率计算器")
st.markdown("---")

# 初始化 Session State
if 'h1_emoji' not in st.session_state:
    st.session_state.h1_emoji = EMOJI_CARDS[0]
if 'h2_emoji' not in st.session_state:
    st.session_state.h2_emoji = [c for c in EMOJI_CARDS if c != st.session_state.h1_emoji][1]
if 'flop_emoji' not in st.session_state:
    st.session_state.flop_emoji = []
if 'turn_emoji' not in st.session_state:
    st.session_state.turn_emoji = ""
if 'river_emoji' not in st.session_state:
    st.session_state.river_emoji = ""

def get_available_cards(exclude_list):
    """获取可用牌列表"""
    return [c for c in EMOJI_CARDS if c not in exclude_list]

def random_hole_cards():
    """随机选择两张手牌"""
    available = get_available_cards([])
    random_hand = random.sample(available, 2)
    st.session_state.h1_emoji = random_hand[0]
    st.session_state.h2_emoji = random_hand[1]

# --- 新增：独立的公共牌随机函数 ---
def random_flop_cards():
    """随机选择 3 张翻牌"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + ([st.session_state.turn_emoji] if st.session_state.turn_emoji else []) + ([st.session_state.river_emoji] if st.session_state.river_emoji else [])
    
    available = get_available_cards(known_cards)
    
    if len(available) >= 3:
        st.session_state.flop_emoji = random.sample(available, 3)
    else:
        st.warning("牌池中没有足够的牌来随机翻牌。")

def random_turn_card():
    """随机选择 1 张转牌"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + st.session_state.flop_emoji + ([st.session_state.river_emoji] if st.session_state.river_emoji else [])
    
    available = get_available_cards(known_cards)

    if len(available) >= 1:
        st.session_state.turn_emoji = random.sample(available, 1)[0]
    else:
        st.session_state.turn_emoji = ""
        st.warning("牌池中没有可用的牌来随机转牌。")

def random_river_card():
    """随机选择 1 张河牌"""
    current_hand = [st.session_state.h1_emoji, st.session_state.h2_emoji]
    known_cards = current_hand + st.session_state.flop_emoji + ([st.session_state.turn_emoji] if st.session_state.turn_emoji else [])
    
    available = get_available_cards(known_cards)

    if len(available) >= 1:
        st.session_state.river_emoji = random.sample(available, 1)[0]
    else:
        st.session_state.river_emoji = ""
        st.warning("牌池中没有可用的牌来随机河牌。")
# --- 结束新增：独立的公共牌随机函数 ---


# ----------------------------------------------------
# 1. 您的手牌 (Hole Cards)
# ----------------------------------------------------
st.header("1. 您的手牌 (Hole Cards)")

# 设置手牌随机按钮
col_h_manual, col_h_random = st.columns([0.7, 0.3])
with col_h_random:
    st.markdown(" ") # 用于对齐
    if st.button("🔀 随机手牌", key="random_hand_btn"):
        random_hole_cards()
        st.rerun() 

# 手牌手动选择
h_col1, h_col2 = col_h_manual.columns(2)
with h_col1:
    h1_emoji = st.selectbox(
        "第一张牌", 
        EMOJI_CARDS, 
        key="h1_emoji", 
        index=EMOJI_CARDS.index(st.session_state.h1_emoji)
    )

# 动态更新第二张牌的选项，排除第一张牌
h2_options = [c for c in EMOJI_CARDS if c != h1_emoji]
try:
    h2_index = h2_options.index(st.session_state.h2_emoji)
except ValueError:
    h2_index = 0
    st.session_state.h2_emoji = h2_options[0] 
    
with h_col2:
    h2_emoji = st.selectbox(
        "第二张牌", 
        h2_options, 
        key="h2_emoji",
        index=h2_index
    )

all_selected_cards = [h1_emoji, h2_emoji]


# ----------------------------------------------------
# 2. 公共牌 (Board)
# ----------------------------------------------------
st.header("2. 公共牌 (Board)")

# --- 翻牌 (Flop) ---
col_f_manual, col_f_random = st.columns([0.7, 0.3])
with col_f_random:
    if st.button("🔀 随机翻牌 (3张)", key="random_flop_btn"):
        random_flop_cards()
        st.rerun()

# 动态更新翻牌选项
board_options_flop = get_available_cards(all_selected_cards)
with col_f_manual:
    flop_emoji = st.multiselect(
        "翻牌 (Flop, 0或3张)", 
        board_options_flop, 
        max_selections=3, 
        default=st.session_state.flop_emoji,
        key="flop_emoji"
    )
all_selected_cards.extend(flop_emoji)

# --- 转牌 (Turn) ---
col_t_manual, col_t_random = st.columns([0.7, 0.3])
with col_t_random:
    if st.button("🔀 随机转牌 (1张)", key="random_turn_btn"):
        random_turn_card()
        st.rerun()

# 动态更新转牌选项
turn_options = [c for c in EMOJI_CARDS if c not in all_selected_cards]
try:
    turn_index = turn_options.index(st.session_state.turn_emoji) + 1 
except ValueError:
    turn_index = 0
    st.session_state.turn_emoji = "" 
    
with col_t_manual:
    turn_emoji = st.selectbox(
        "转牌 (Turn, 0或1张)", 
        [""] + turn_options, 
        index=turn_index,
        key="turn_emoji"
    )
if turn_emoji:
    all_selected_cards.append(turn_emoji)

# --- 河牌 (River) ---
col_r_manual, col_r_random = st.columns([0.7, 0.3])
with col_r_random:
    if st.button("🔀 随机河牌 (1张)", key="random_river_btn"):
        random_river_card()
        st.rerun()

# 动态更新河牌选项
river_options = [c for c in EMOJI_CARDS if c not in all_selected_cards]
try:
    river_index = river_options.index(st.session_state.river_emoji) + 1 
except ValueError:
    river_index = 0
    st.session_state.river_emoji = "" 
    
with col_r_manual:
    river_emoji = st.selectbox(
        "河牌 (River, 0或1张)", 
        [""] + river_options, 
        index=river_index,
        key="river_emoji"
    )
if river_emoji:
    all_selected_cards.append(river_emoji)


# ----------------------------------------------------
# 3. 结果计算
# ----------------------------------------------------
st.markdown("---")
if st.button("🚀 计算当前胜率"):
    
    # 检查牌是否有重复
    if h1_emoji == h2_emoji:
        st.error("⚠️ 您的两张手牌不能相同。")
    elif len(set(all_selected_cards)) != len(all_selected_cards):
        st.error("⚠️ 牌池中不能有重复的牌。请检查您的选择。")
    else:
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
            with st.spinner('正在计算胜率...这在公共牌张数较多时可能需要更长时间。'):
                # 调用更新后的函数
                equity, calc_type = calculate_equity(player_hand_int, board_int, simulations=10000)
                
                st.success("✅ **计算完成！**")
                st.markdown(f"## 您的当前胜率是: **{equity * 100:.2f}%**")
                
                st.info(f"计算类型：{calc_type}。")
        else:
            st.error("请选择您的两张手牌。")