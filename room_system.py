#!/usr/bin/env python3
"""
ASD Therapy Game - 50 Room System
مثل Royal Kingdom - كل غرفة therapy مختلفة
Score → Level Up → Room Unlocks
"""

# ========== تعريف الـ 50 غرفة ==========
ROOMS = {
    # ===== WORLD 1: Greeting & Communication =====
    1:  {"name":"Welcome Room",        "world":1, "world_name":"Greetings",
         "protocol":"greeting",        "required_score":0,
         "target_score":50,            "color":[0.4,0.8,1.0,1],
         "description":"Say hello to Pepper!",
         "therapy_actions":["greet","wave","say_name"],
         "objects":["welcome_sign","door","mirror"],
         "reward":"🌟 First Star!"},

    2:  {"name":"Hello World",         "world":1, "world_name":"Greetings",
         "protocol":"greeting",        "required_score":50,
         "target_score":100,           "color":[0.4,0.8,1.0,1],
         "description":"Learn to say Hello and Goodbye",
         "therapy_actions":["say_hello","say_goodbye","wave"],
         "objects":["clock","door","name_cards"],
         "reward":"👋 Wave Master!"},

    3:  {"name":"Name Game",           "world":1, "world_name":"Greetings",
         "protocol":"DTT",             "required_score":100,
         "target_score":160,           "color":[0.4,0.8,1.0,1],
         "description":"Respond when your name is called",
         "therapy_actions":["respond_to_name","eye_contact","turn_head"],
         "objects":["name_cards","bell","photo"],
         "reward":"📛 Name Star!"},

    4:  {"name":"Eye Contact Room",    "world":1, "world_name":"Greetings",
         "protocol":"joint_attention", "required_score":160,
         "target_score":230,           "color":[0.4,0.8,1.0,1],
         "description":"Look at Pepper's eyes",
         "therapy_actions":["eye_contact","follow_gaze","look_at_me"],
         "objects":["mirror","flashlight","puppet"],
         "reward":"👁️ Eye Contact Pro!"},

    5:  {"name":"Greeting Master",     "world":1, "world_name":"Greetings",
         "protocol":"NET",             "required_score":230,
         "target_score":320,           "color":[0.4,0.8,1.0,1],
         "description":"Master all greetings!",
         "therapy_actions":["greet","wave","eye_contact","say_name"],
         "objects":["trophy","certificate","party_items"],
         "reward":"🏆 Greeting Champion!"},

    # ===== WORLD 2: Emotion Recognition =====
    6:  {"name":"Happy Room",          "world":2, "world_name":"Emotions",
         "protocol":"emotion_recognition","required_score":320,
         "target_score":400,           "color":[1.0,0.9,0.2,1],
         "description":"Learn the Happy face!",
         "therapy_actions":["show_happy","copy_happy","name_happy"],
         "objects":["emotion_cards","mirror","smiley_ball"],
         "reward":"😊 Happy Face!"},

    7:  {"name":"Sad Room",            "world":2, "world_name":"Emotions",
         "protocol":"emotion_recognition","required_score":400,
         "target_score":490,           "color":[1.0,0.9,0.2,1],
         "description":"Learn the Sad face",
         "therapy_actions":["show_sad","copy_sad","name_sad"],
         "objects":["emotion_cards","tissue_box","blue_items"],
         "reward":"😢 Empathy Star!"},

    8:  {"name":"Angry Room",          "world":2, "world_name":"Emotions",
         "protocol":"emotion_recognition","required_score":490,
         "target_score":590,           "color":[1.0,0.9,0.2,1],
         "description":"Learn the Angry face",
         "therapy_actions":["show_angry","name_angry","calm_strategy"],
         "objects":["emotion_cards","stress_ball","calm_corner"],
         "reward":"😠 Anger Manager!"},

    9:  {"name":"Scared Room",         "world":2, "world_name":"Emotions",
         "protocol":"emotion_recognition","required_score":590,
         "target_score":700,           "color":[1.0,0.9,0.2,1],
         "description":"Learn the Scared face",
         "therapy_actions":["show_scared","name_scared","comfort"],
         "objects":["emotion_cards","safety_blanket","nightlight"],
         "reward":"😱 Brave Star!"},

    10: {"name":"Emotion Master",      "world":2, "world_name":"Emotions",
         "protocol":"emotion_recognition","required_score":700,
         "target_score":830,           "color":[1.0,0.9,0.2,1],
         "description":"All 4 emotions challenge!",
         "therapy_actions":["all_emotions","emotion_game","emotion_story"],
         "objects":["all_cards","emotion_board","prize_box"],
         "reward":"🎭 Emotion Champion!"},

    # ===== WORLD 3: Joint Attention =====
    11: {"name":"Look Here!",          "world":3, "world_name":"Joint Attention",
         "protocol":"joint_attention", "required_score":830,
         "target_score":980,           "color":[0.5,1.0,0.5,1],
         "description":"Follow where Pepper points",
         "therapy_actions":["follow_point","look_at_object","respond_to_gaze"],
         "objects":["red_ball","yellow_block","pointing_glove"],
         "reward":"👀 Looker Star!"},

    12: {"name":"Ball Room",           "world":3, "world_name":"Joint Attention",
         "protocol":"joint_attention", "required_score":980,
         "target_score":1140,          "color":[0.5,1.0,0.5,1],
         "description":"Follow the ball with your eyes",
         "therapy_actions":["track_ball","point_to_ball","catch_ball"],
         "objects":["red_ball","blue_ball","green_ball"],
         "reward":"🎯 Ball Tracker!"},

    13: {"name":"Picture Room",        "world":3, "world_name":"Joint Attention",
         "protocol":"TEACCH",          "required_score":1140,
         "target_score":1310,          "color":[0.5,1.0,0.5,1],
         "description":"Look at pictures together",
         "therapy_actions":["look_at_picture","point_in_picture","name_picture"],
         "objects":["picture_book","animal_cards","photo_album"],
         "reward":"📸 Picture Pro!"},

    14: {"name":"Gaze Room",           "world":3, "world_name":"Joint Attention",
         "protocol":"joint_attention", "required_score":1310,
         "target_score":1490,          "color":[0.5,1.0,0.5,1],
         "description":"Follow Pepper's gaze",
         "therapy_actions":["follow_gaze","check_back","shared_attention"],
         "objects":["window","interesting_object","gaze_target"],
         "reward":"🎯 Gaze Master!"},

    15: {"name":"Attention Champion",  "world":3, "world_name":"Joint Attention",
         "protocol":"joint_attention", "required_score":1490,
         "target_score":1700,          "color":[0.5,1.0,0.5,1],
         "description":"Joint attention master challenge",
         "therapy_actions":["all_JA_skills","JA_game","JA_story"],
         "objects":["all_objects","trophy","star_chart"],
         "reward":"⭐ Attention Champion!"},

    # ===== WORLD 4: DTT Training =====
    16: {"name":"Instruction Room",    "world":4, "world_name":"DTT Training",
         "protocol":"DTT",             "required_score":1700,
         "target_score":1930,          "color":[1.0,0.5,0.2,1],
         "description":"Follow one-step instructions",
         "therapy_actions":["clap","stand_up","sit_down","touch_nose"],
         "objects":["instruction_cards","reward_box","timer"],
         "reward":"📋 Instruction Pro!"},

    17: {"name":"Body Parts Room",     "world":4, "world_name":"DTT Training",
         "protocol":"DTT",             "required_score":1930,
         "target_score":2180,          "color":[1.0,0.5,0.2,1],
         "description":"Touch body parts correctly",
         "therapy_actions":["touch_nose","touch_ears","touch_head","touch_tummy"],
         "objects":["body_chart","mirror","body_puzzle"],
         "reward":"🫀 Body Expert!"},

    18: {"name":"Object Room",         "world":4, "world_name":"DTT Training",
         "protocol":"DTT",             "required_score":2180,
         "target_score":2450,          "color":[1.0,0.5,0.2,1],
         "description":"Name and point to objects",
         "therapy_actions":["name_object","point_object","give_object"],
         "objects":["cup","ball","book","chair","table"],
         "reward":"🏷️ Object Master!"},

    19: {"name":"Color Room",          "world":4, "world_name":"DTT Training",
         "protocol":"DTT",             "required_score":2450,
         "target_score":2740,          "color":[1.0,0.5,0.2,1],
         "description":"Learn colors",
         "therapy_actions":["name_color","sort_colors","match_colors"],
         "objects":["red_block","blue_block","green_block","yellow_block"],
         "reward":"🌈 Color Champion!"},

    20: {"name":"DTT Master Room",     "world":4, "world_name":"DTT Training",
         "protocol":"DTT",             "required_score":2740,
         "target_score":3060,          "color":[1.0,0.5,0.2,1],
         "description":"DTT final challenge",
         "therapy_actions":["all_DTT","DTT_game","DTT_challenge"],
         "objects":["all_objects","trophy","diploma"],
         "reward":"🎓 DTT Graduate!"},

    # ===== WORLD 5: Sensory & Music =====
    21: {"name":"Music Room",          "world":5, "world_name":"Sensory",
         "protocol":"sensory",         "required_score":3060,
         "target_score":3400,          "color":[0.8,0.4,1.0,1],
         "description":"Listen and respond to music",
         "therapy_actions":["listen_music","clap_rhythm","move_to_music"],
         "objects":["drum","xylophone","music_player","tambourine"],
         "reward":"🎵 Music Lover!"},

    22: {"name":"Calm Room",           "world":5, "world_name":"Sensory",
         "protocol":"sensory",         "required_score":3400,
         "target_score":3760,          "color":[0.8,0.4,1.0,1],
         "description":"Relaxation and breathing",
         "therapy_actions":["deep_breathe","count_breathe","body_scan"],
         "objects":["cushions","calm_light","breathing_ball","zen_garden"],
         "reward":"🧘 Calm Master!"},

    23: {"name":"Touch Room",          "world":5, "world_name":"Sensory",
         "protocol":"sensory",         "required_score":3760,
         "target_score":4140,          "color":[0.8,0.4,1.0,1],
         "description":"Explore different textures",
         "therapy_actions":["touch_soft","touch_hard","identify_texture"],
         "objects":["soft_ball","rough_stone","smooth_wood","feather"],
         "reward":"✋ Touch Explorer!"},

    24: {"name":"Sound Room",          "world":5, "world_name":"Sensory",
         "protocol":"sensory",         "required_score":4140,
         "target_score":4540,          "color":[0.8,0.4,1.0,1],
         "description":"Identify different sounds",
         "therapy_actions":["identify_sound","loud_quiet","animal_sounds"],
         "objects":["sound_box","earphones","sound_cards"],
         "reward":"👂 Sound Expert!"},

    25: {"name":"Sensory Champion",    "world":5, "world_name":"Sensory",
         "protocol":"sensory",         "required_score":4540,
         "target_score":4980,          "color":[0.8,0.4,1.0,1],
         "description":"Sensory master challenge",
         "therapy_actions":["all_sensory","sensory_story","sensory_game"],
         "objects":["sensory_kit","trophy","certificate"],
         "reward":"🌟 Sensory Champion!"},

    # ===== WORLD 6: Movement & Sports =====
    26: {"name":"Walking Room",        "world":6, "world_name":"Movement",
         "protocol":"motor",           "required_score":4980,
         "target_score":5450,          "color":[0.2,0.9,0.7,1],
         "description":"Walk and move with Pepper",
         "therapy_actions":["walk_forward","walk_backward","follow_path"],
         "objects":["footprints","path_markers","walking_track"],
         "reward":"🚶 Walker Star!"},

    27: {"name":"Jumping Room",        "world":6, "world_name":"Movement",
         "protocol":"motor",           "required_score":5450,
         "target_score":5950,          "color":[0.2,0.9,0.7,1],
         "description":"Jump and hop exercises",
         "therapy_actions":["jump","hop","jump_over","jumping_jacks"],
         "objects":["trampoline","hurdles","jump_mat","rope"],
         "reward":"🦘 Jumping Star!"},

    28: {"name":"Ball Sports Room",    "world":6, "world_name":"Movement",
         "protocol":"motor",           "required_score":5950,
         "target_score":6480,          "color":[0.2,0.9,0.7,1],
         "description":"Play ball with Pepper",
         "therapy_actions":["throw_ball","catch_ball","kick_ball","roll_ball"],
         "objects":["soccer_ball","basketball","tennis_ball","goal"],
         "reward":"⚽ Sports Star!"},

    29: {"name":"Balance Room",        "world":6, "world_name":"Movement",
         "protocol":"motor",           "required_score":6480,
         "target_score":7040,          "color":[0.2,0.9,0.7,1],
         "description":"Balance exercises",
         "therapy_actions":["stand_one_leg","walk_line","balance_beam"],
         "objects":["balance_beam","wobble_board","stepping_stones"],
         "reward":"⚖️ Balance Master!"},

    30: {"name":"Sports Champion",     "world":6, "world_name":"Movement",
         "protocol":"motor",           "required_score":7040,
         "target_score":7640,          "color":[0.2,0.9,0.7,1],
         "description":"Sports master challenge",
         "therapy_actions":["all_sports","sports_game","mini_olympics"],
         "objects":["all_equipment","medals","podium"],
         "reward":"🥇 Sports Champion!"},

    # ===== WORLD 7: Art & Creativity =====
    31: {"name":"Drawing Room",        "world":7, "world_name":"Art",
         "protocol":"creative",        "required_score":7640,
         "target_score":8280,          "color":[1.0,0.7,0.8,1],
         "description":"Draw with Pepper",
         "therapy_actions":["draw_circle","draw_line","copy_shape","color_picture"],
         "objects":["paper","crayons","markers","easel"],
         "reward":"🎨 Artist Star!"},

    32: {"name":"Building Room",       "world":7, "world_name":"Art",
         "protocol":"creative",        "required_score":8280,
         "target_score":8960,          "color":[1.0,0.7,0.8,1],
         "description":"Build with blocks",
         "therapy_actions":["stack_blocks","copy_structure","build_tower"],
         "objects":["lego","wooden_blocks","duplo","pattern_cards"],
         "reward":"🏗️ Builder Star!"},

    33: {"name":"Music Making Room",   "world":7, "world_name":"Art",
         "protocol":"creative",        "required_score":8960,
         "target_score":9680,          "color":[1.0,0.7,0.8,1],
         "description":"Make music with Pepper",
         "therapy_actions":["play_drum","copy_rhythm","make_song"],
         "objects":["drum","piano_keys","rhythm_sticks","bells"],
         "reward":"🥁 Music Maker!"},

    34: {"name":"Story Room",          "world":7, "world_name":"Art",
         "protocol":"creative",        "required_score":9680,
         "target_score":10440,         "color":[1.0,0.7,0.8,1],
         "description":"Tell stories with pictures",
         "therapy_actions":["sequence_story","tell_story","act_story"],
         "objects":["story_cards","puppets","story_book","stage"],
         "reward":"📖 Story Teller!"},

    35: {"name":"Art Champion",        "world":7, "world_name":"Art",
         "protocol":"creative",        "required_score":10440,
         "target_score":11240,         "color":[1.0,0.7,0.8,1],
         "description":"Art master challenge",
         "therapy_actions":["art_show","creative_project","art_game"],
         "objects":["all_art_supplies","gallery_wall","prize"],
         "reward":"🖼️ Art Champion!"},

    # ===== WORLD 8: Problem Solving =====
    36: {"name":"Puzzle Room",         "world":8, "world_name":"Problem Solving",
         "protocol":"cognitive",       "required_score":11240,
         "target_score":12100,         "color":[0.9,0.6,0.2,1],
         "description":"Solve simple puzzles",
         "therapy_actions":["simple_puzzle","shape_puzzle","picture_puzzle"],
         "objects":["3piece_puzzle","shape_sorter","form_board"],
         "reward":"🧩 Puzzle Solver!"},

    37: {"name":"Sorting Room",        "world":8, "world_name":"Problem Solving",
         "protocol":"cognitive",       "required_score":12100,
         "target_score":13000,         "color":[0.9,0.6,0.2,1],
         "description":"Sort objects by color and shape",
         "therapy_actions":["sort_color","sort_shape","sort_size","match"],
         "objects":["sorting_tray","colored_objects","shape_blocks"],
         "reward":"📊 Sorting Expert!"},

    38: {"name":"Sequence Room",       "world":8, "world_name":"Problem Solving",
         "protocol":"TEACCH",          "required_score":13000,
         "target_score":13950,         "color":[0.9,0.6,0.2,1],
         "description":"Put things in order",
         "therapy_actions":["sequence_pictures","daily_routine","what_next"],
         "objects":["sequence_cards","routine_board","visual_schedule"],
         "reward":"📅 Sequence Master!"},

    39: {"name":"Choice Room",         "world":8, "world_name":"Problem Solving",
         "protocol":"PRT",             "required_score":13950,
         "target_score":14950,         "color":[0.9,0.6,0.2,1],
         "description":"Make choices and decisions",
         "therapy_actions":["choose_between_two","preference","decision"],
         "objects":["choice_board","PECS_cards","preference_items"],
         "reward":"✅ Decision Maker!"},

    40: {"name":"Problem Champion",    "world":8, "world_name":"Problem Solving",
         "protocol":"cognitive",       "required_score":14950,
         "target_score":16000,         "color":[0.9,0.6,0.2,1],
         "description":"Problem solving master challenge",
         "therapy_actions":["all_cognitive","brain_game","challenge"],
         "objects":["all_puzzles","genius_badge","trophy"],
         "reward":"🧠 Genius Star!"},

    # ===== WORLD 9: Social Skills =====
    41: {"name":"Sharing Room",        "world":9, "world_name":"Social Skills",
         "protocol":"social",          "required_score":16000,
         "target_score":17100,         "color":[0.5,0.7,1.0,1],
         "description":"Learn to share with others",
         "therapy_actions":["share_toy","take_turns","give_receive"],
         "objects":["toys","sharing_timer","turn_taking_board"],
         "reward":"🤝 Sharing Star!"},

    42: {"name":"Waiting Room",        "world":9, "world_name":"Social Skills",
         "protocol":"social",          "required_score":17100,
         "target_score":18250,         "color":[0.5,0.7,1.0,1],
         "description":"Practice waiting patiently",
         "therapy_actions":["wait_turn","first_then","patience_game"],
         "objects":["waiting_timer","visual_countdown","patience_chart"],
         "reward":"⏰ Patience Master!"},

    43: {"name":"Play Together Room",  "world":9, "world_name":"Social Skills",
         "protocol":"social",          "required_score":18250,
         "target_score":19450,         "color":[0.5,0.7,1.0,1],
         "description":"Play games with Pepper",
         "therapy_actions":["play_game","cooperative_play","pretend_play"],
         "objects":["board_game","play_kitchen","dress_up","pretend_items"],
         "reward":"🎮 Play Partner!"},

    44: {"name":"Helping Room",        "world":9, "world_name":"Social Skills",
         "protocol":"social",          "required_score":19450,
         "target_score":20700,         "color":[0.5,0.7,1.0,1],
         "description":"Learn to help others",
         "therapy_actions":["help_clean","help_carry","ask_for_help"],
         "objects":["cleaning_items","helper_chart","helping_hands"],
         "reward":"🦸 Helper Star!"},

    45: {"name":"Social Champion",     "world":9, "world_name":"Social Skills",
         "protocol":"social",          "required_score":20700,
         "target_score":22000,         "color":[0.5,0.7,1.0,1],
         "description":"Social skills master challenge",
         "therapy_actions":["social_story","role_play","social_game"],
         "objects":["social_scripts","role_play_items","social_trophy"],
         "reward":"👑 Social Champion!"},

    # ===== WORLD 10: Master Challenges =====
    46: {"name":"Memory Palace",       "world":10,"world_name":"Master",
         "protocol":"cognitive",       "required_score":22000,
         "target_score":23500,         "color":[1.0,0.85,0.0,1],
         "description":"Remember sequences and patterns",
         "therapy_actions":["memory_game","pattern_recall","sequence_memory"],
         "objects":["memory_cards","pattern_board","recall_game"],
         "reward":"🧠 Memory Master!"},

    47: {"name":"Communication Lab",   "world":10,"world_name":"Master",
         "protocol":"AAC",             "required_score":23500,
         "target_score":25200,         "color":[1.0,0.85,0.0,1],
         "description":"Advanced communication skills",
         "therapy_actions":["PECS","AAC_device","sentence_building"],
         "objects":["PECS_book","communication_board","AAC_tablet"],
         "reward":"💬 Communication Expert!"},

    48: {"name":"Friendship Room",     "world":10,"world_name":"Master",
         "protocol":"social",          "required_score":25200,
         "target_score":27100,         "color":[1.0,0.85,0.0,1],
         "description":"Advanced friendship skills",
         "therapy_actions":["start_conversation","maintain_conversation","friendship_skills"],
         "objects":["friendship_cards","conversation_starters","friend_photo"],
         "reward":"👫 Friendship Star!"},

    49: {"name":"Independence Room",   "world":10,"world_name":"Master",
         "protocol":"life_skills",     "required_score":27100,
         "target_score":29200,         "color":[1.0,0.85,0.0,1],
         "description":"Daily living skills",
         "therapy_actions":["wash_hands","dress_self","prepare_snack","tidy_up"],
         "objects":["sink","clothes","snack_items","tidying_tools"],
         "reward":"🌟 Independence Star!"},

    50: {"name":"CHAMPION HALL",       "world":10,"world_name":"Master",
         "protocol":"all",             "required_score":29200,
         "target_score":31500,         "color":[1.0,0.8,0.0,1],
         "description":"THE ULTIMATE CHALLENGE - All skills!",
         "therapy_actions":["all_skills","final_challenge","celebration"],
         "objects":["all_items","hall_of_fame","golden_trophy","fireworks"],
         "reward":"🏆👑 ULTIMATE CHAMPION!"},
}

# ========== نظام المستويات ==========
WORLD_NAMES = {
    1:"🗣️ Greetings",    2:"🎭 Emotions",      3:"👀 Joint Attention",
    4:"📚 DTT Training", 5:"🎵 Sensory",        6:"🏃 Movement",
    7:"🎨 Art",          8:"🧩 Problem Solving", 9:"👥 Social Skills",
    10:"⭐ Master Level"
}

class RoomSystem:
    def __init__(self):
        self.total_score    = 0
        self.current_room   = 1
        self.unlocked_rooms = {1}
        self.completed_rooms= set()
        self.room_scores    = {}  # room_id → score earned
        self.stars          = {}  # room_id → stars (1-3)
        print("✅ Room System initialized - 50 rooms ready!")

    def get_current_room(self):
        return ROOMS[self.current_room]

    def get_room(self, room_id):
        return ROOMS.get(room_id)

    def add_score(self, points, room_id=None):
        """إضافة نقاط وفحص فتح غرف جديدة"""
        self.total_score += points
        if room_id:
            self.room_scores[room_id] = self.room_scores.get(room_id, 0) + points

        newly_unlocked = []
        for rid, room in ROOMS.items():
            if rid not in self.unlocked_rooms:
                if self.total_score >= room["required_score"]:
                    self.unlocked_rooms.add(rid)
                    newly_unlocked.append(rid)
                    print(f"🔓 UNLOCKED: Room {rid} - {room['name']}!")

        return newly_unlocked

    def complete_room(self, room_id, score_earned):
        """إكمال غرفة وحساب النجوم"""
        room = ROOMS[room_id]
        self.completed_rooms.add(room_id)
        target = room["target_score"] - room["required_score"]
        pct = score_earned / max(1, target) * 100

        if pct >= 90:   stars = 3
        elif pct >= 60: stars = 2
        else:           stars = 1

        self.stars[room_id] = stars
        print(f"✅ Room {room_id} complete! {'⭐'*stars} ({pct:.0f}%)")
        print(f"🎁 Reward: {room['reward']}")
        return stars

    def go_to_room(self, room_id):
        """الانتقال لغرفة"""
        if room_id not in self.unlocked_rooms:
            req = ROOMS[room_id]["required_score"]
            print(f"🔒 Room {room_id} locked! Need {req} points (you have {self.total_score})")
            return False
        self.current_room = room_id
        room = ROOMS[room_id]
        print(f"\n🚪 Entering Room {room_id}: {room['name']}")
        print(f"   World: {room['world_name']}")
        print(f"   Protocol: {room['protocol'].upper()}")
        print(f"   Goal: {room['description']}")
        return True

    def get_progress(self):
        """تقرير التقدم"""
        total    = len(ROOMS)
        unlocked = len(self.unlocked_rooms)
        complete = len(self.completed_rooms)
        total_stars = sum(self.stars.values())
        pct = round(complete / total * 100, 1)

        return {
            "total_score":   self.total_score,
            "current_room":  self.current_room,
            "unlocked":      unlocked,
            "completed":     complete,
            "total_rooms":   total,
            "completion_pct":pct,
            "total_stars":   total_stars,
            "max_stars":     total * 3
        }

    def print_map(self, world=None):
        """طباعة خريطة الغرف"""
        print("\n" + "="*65)
        print(f"🗺️  THERAPY WORLD MAP  |  Score: {self.total_score}")
        print("="*65)
        for w in range(1, 11):
            if world and w != world:
                continue
            print(f"\n{WORLD_NAMES[w]}")
            print("-"*40)
            for rid, room in ROOMS.items():
                if room["world"] != w:
                    continue
                if rid in self.completed_rooms:
                    stars = "⭐" * self.stars.get(rid, 1)
                    status = f"✅ {stars}"
                elif rid in self.unlocked_rooms:
                    status = "🔓 OPEN"
                else:
                    req = room["required_score"]
                    status = f"🔒 ({req} pts)"
                print(f"  Room {rid:2d}: {room['name']:25s} {status}")
        print("="*65)
        prog = self.get_progress()
        print(f"Progress: {prog['completed']}/{prog['total_rooms']} rooms | "
              f"{prog['total_stars']}/{prog['max_stars']} stars | "
              f"{prog['completion_pct']}%")


# ===== اختبار =====
if __name__ == "__main__":
    rs = RoomSystem()
    print("\n🎮 Room System Test")
    rs.print_map(world=1)

    print("\n--- Simulating gameplay ---")
    rs.add_score(350)
    rs.go_to_room(2)
    rs.complete_room(1, 50)
    rs.add_score(500)
    rs.go_to_room(3)
    rs.print_map(world=1)

    prog = rs.get_progress()
    print(f"\n📊 Progress: {prog}")
