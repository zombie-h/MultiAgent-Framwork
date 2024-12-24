import json
import copy
from datetime import datetime
import configparser
import os
import yaml

from openai import OpenAI

print("Current working directory:", os.getcwd())

config = configparser.ConfigParser()
# Adjust path to look for config.ini in AImodule regardless of the current directory
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
config_path = os.path.join(base_dir, 'config.ini')
config.read(config_path)

print("Config sections found:", config.sections())

if 'OpenAI' not in config:
    print("Error: 'OpenAI' section not found in config.ini")
openai_key = config['OpenAI']['key']
client = OpenAI(api_key=openai_key)

yaml_path = os.path.join(base_dir, 'char_config.yaml')

# Load the YAML file
with open(yaml_path, 'r', encoding='utf-8' ) as file:
    char_config = yaml.safe_load(file)
    print("YAML content loaded successfully.")


############################################
# Memory and Reflection Related Functions
############################################

def get_embedding(text, model="text-embedding-3-small"):
    text = str(text.replace("\n", " "))
    return client.embeddings.create(input = text, model=model).data[0].embedding

def get_importance(mem_single_str):
    prompt = f'''
    On the scale of 1 to 10, where 1 is purely mundane (e.g., brushing teeth, making bed) and 10 is extremely poignant (e.g., a breakup, college acceptance), rate the likely poignancy of the following piece of memory.

    Memory:
    {mem_single_str}

    Rating: <fill in>

    Just give me a number with no extra txt.
    '''
    completion = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {"role": "system", "content": "You are a good instruction-to-language translator. You will process the information given to you and give instruction in a fixed format."},
        {"role": "user", "content": prompt}
      ]
    )
    output = completion.choices[0].message.content
    print("Function: get_importance")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def condenseMemoriesAndReflections(npc_name, npc_description, npc_context, recent_schedule_str, memories_str, reflections_str):
    prompt = f'''
    You are a NPC character in a simulated town.
    You are {npc_name}, {npc_description}.

    Your context now:
    {npc_context}

    Your calendar of the day:
    {recent_schedule_str}

    You are given the memories and reflections of the NPC.
    Your past memories and experiences:
    {memories_str}
    Your reflection past experiences and events:
    {reflections_str}
    Please provide a condensed version of the memories and reflections, focusing on the most important and relevant details that will be used to make decision on next action.
    '''
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", "content": "You are a great schedule planner and instruction giver. You will process the information given to you and give instruction."},
        {"role": "user", "content": prompt}
      ]
    )
    output = completion.choices[0].message.content
    print("Function: condenseMemoriesAndReflections")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def needDeepTalk(memories, reflections, npc_context, npc_action, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']

    prompt = f"""
    You are an expert in determining narrative significance for NPC dialogues.

    Based on the following details, determine if You should deliver a meaningful speech:

    You are {npc_name}, {npc_description}.

    Your past memories and experiences:
    {memories}

    Reflections of you:
    {reflections}

    Your current Context:
    {npc_context}

    Your upcoming Action:
    {npc_action}

    Please return "True" if a meaningful speech is warranted (e.g., when you reading, thinking, analyzing, dreaming, etc.), 
    or "False" if not.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an assistant designed to analyze narrative elements and make decisions."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    output = completion.choices[0].message.content.strip()
    print("Function: needDeepTalk")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    if output.lower() == "true":
        return True
    elif output.lower() == "false":
        return False
    else:
        return False

def generate_reflection_new(memories_str, reflections_str, java_input_str, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']

    question_1 = "Given only the information above, what are 5 most salient high-level questions we can answer about the subjects in the statements during the daily life not included in the npc current information? Moreover, what is your 3 recent goals, and 3 long terms goals? Do you want to make adjustment to your goals, and how far are you there to achieving those goals?"

    prompt_1 = f'''
    You are {npc_name}, {npc_description}, .

    Your context now:
    {java_input_str}

    Your memeories:
    {memories_str}

    Your prior reflections on past experiences and events:
    {reflections_str}

    {question_1}
    '''
    completion_1 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a deep thinker and reflective analyst."},
            {"role": "user", "content": prompt_1.strip()}
        ]
    )
    question_1_answer = completion_1.choices[0].message.content

    question_2 = "What 5 high-level insights can you infer from the above statements not included in the information of the npc?."
    prompt_2 = f'''
    You are {npc_name}, {npc_description}, .

    Your context now:
    {java_input_str}

    Your memeories:
    {memories_str}

    Your prior reflections on past experiences and events:
    {reflections_str}

    {question_2} in the following directions:
    {question_1_answer}

    Just give me the insights, do not provide explanations or any other information.
    '''
    completion_2 = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a deep thinker and reflective analyst."},
            {"role": "user", "content": prompt_2.strip()}
        ]
    )
    question_2_answer = completion_2.choices[0].message.content
    print("Function: generate_reflection_new (Step 1)")
    print("Prompt:")
    print(prompt_1)
    print("Output (Step 1):")
    print(question_1_answer)
    print("\n\n")
    print("Function: generate_reflection_new (Step 2)")
    print("Prompt:")
    print(prompt_2)
    print("Output (Step 2):")
    print(question_2_answer)
    print("\n\n")
    return question_2_answer


############################################
# Scheduling Related Functions
############################################

def onlyMostRecentSchedule(npc_context, schedule_str):
    prompt = f'''
    You are a NPC character in a simulated town.
    You are given the current context of the NPC and the schedule for the day.

    Your context now:
    {npc_context}

    Your calendar of the day:
    {schedule_str}

    Please provide only the most recent schedule item from the calendar that are relevent to the context, and are need for making decision about what to do next.
    '''
    completion = client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[
        {"role": "system", "content": "You are a great schedule planner and instruction giver. You will process the information given to you and give instruction."},
        {"role": "user", "content": prompt}
      ]
    )
    output = completion.choices[0].message.content
    print("Function: onlyMostRecentSchedule")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def generate_schedule(current_schedule, memories, reflections, npc_context, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    npc_schedule = npc.get('schedule', [])

    prompt = f"""
    You are {npc_name}, {npc_description}.

    You are living in a simulated world. 

    This is a example typical schedule for you, you can adjust it to the current situation:
    {npc_schedule}

    Your prior schedule:
    {current_schedule}

    Your past memeories:
    {memories}

    Your reflections on past experiences and events:
    {reflections}

    Your context:
    {npc_context}

    Please create a new detailed schedule using 24-hour time format for the NPC for today, adapting to the current situation.
    """
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a good instruction-to-language translator. You will process the information given to you and give instructions in a fixed format."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    output = completion.choices[0].message.content
    print("Function: generate_schedule")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def need_new_schedule(current_schedule, memories, reflections, npc_context, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']

    prompt = f"""
    You are {npc_name}, {npc_description}, .

    You are living in a simulated world. 

    Your prior schedule:
    {current_schedule}

    Your memeories:
    {memories}

    Your reflections on past experiences and events:
    {reflections}

    Your context:
    {npc_context}

    Based on the above, do need a new schedule for the rest of the day? 
    Respond only with 'yes' or 'no'.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant designed to determine whether the NPC needs a new schedule. "
                    "Analyze the provided information and respond with 'yes' if a new schedule is needed or 'no' otherwise."
                )
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    response = completion.choices[0].message.content.strip().lower()
    print("Function: need_new_schedule")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(response)
    print("\n\n")
    if response == 'yes':
        return True
    elif response == 'no':
        return False
    else:
        return False


############################################
# Action Decision Functions
############################################

def processInputGiveWhatToDo(memories_str, reflections_str, schedule_str, npc_context, npcId, special_instruction = ''):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    available_actions = npc.get('availableActions', [])

    npc_action = ""
    for action in available_actions:
        npc_action += (
            f"- **{action['actionName']}**: {action['description']} (location: {action['location']})\n"
        )

    recent_schedule_str = onlyMostRecentSchedule(npc_context, schedule_str)
    
    prompt = f'''
    You are {npc_name}, {npc_description}.
    You are one of the characters in the town, here are all the characters in the town:
    - Satoshi, inventor of the Bitcoin.
    - Musk, Elon Musk, the CEO of Tesla, SpaceX, and Neuralink.
    - Pepe, a meme character, live as a shop owner in the town.
    - Popcat, a meme character, a fisherman in the town.
    - Pippin, a meme character, a coffee maker in the town.

    Your recent schedule:
      {recent_schedule_str}

    Current time and information: {npc_context}

    Your relevent memeories:
    {memories_str}

    Your reflections:
    {reflections_str}

    Tell me what you should do next, choosing one (include the location) from available Actions:
    {npc_action}
    {special_instruction if special_instruction else ''}

    What should you do next? Choose a single action. Provide your name, action name, location, duration(needs to be over 30 minutes at least, if time not allow, jump to next action on schedule), and a short explanation.
    output format and example:
        - {npc_name} using computer at the computer desk for 2 hours. He surf the internet for fishing tutorial.
    '''
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", "content": "You are a great schedule planner and instruction giver. You will process the information give to you and give instruction."},
        {"role": "user", "content": prompt}
      ]
    )
    output = completion.choices[0].message.content
    print("Function: processInputGiveWhatToDo")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def talkToSomeone(memories_str, reflections_str, schedule_str, npc_context, npcId, isFinding, targetNPC = None, special_instruction = '', max_tokens=20):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    npc_way_of_speak = npc['announcements']
    format_instructions = npc_way_of_speak.get('Format', '').lstrip('> ').strip()
    tone_instructions = npc_way_of_speak.get('Tone', '').lstrip('> ').strip() 
    talk_examples = npc_way_of_speak.get('Talk', '').lstrip('> ').strip()

    recent_schedule_str = onlyMostRecentSchedule(npc_context, schedule_str)

    finder_instruction = ""
    if isFinding:
        finder_instruction = ''' Your calendar of the day, try to follow your schedule, but fill free to adjust to the current situation: 
                            ''' + recent_schedule_str + ''' Try to wrap up the conversation if you need to do other things on your calendar.'''

    # Split the format instructions into individual parts
    format_parts = []
    current_text = format_instructions
    for i in range(1, 5):
        if f"{i}." in current_text:
            part = current_text.split(f"{i}.")[1]
            if f"{i+1}." in part:
                part = part.split(f"{i+1}.")[0]
            format_parts.append(part.strip())
            current_text = current_text.split(f"{i}.")[1]

    # Determine which format to use based on context
    prompt_format_selection = f'''
    Based on the following context, determine which conversation format (1-4) is most appropriate:

    Speaking to: {targetNPC if targetNPC else 'someone'}
    Current context: {npc_context}
    Special instruction: {special_instruction}

    Format options:
    1. {format_parts[0]} (Use for: Starting conversations, introductions)
    2. {format_parts[1]} (Use for: Responding to others, continuing dialogue)
    3. {format_parts[2]} (Use for: Deep discussions, sharing insights)
    4. {format_parts[3]} (Use for: Concluding conversations, making final points)

    Return only the number (1-4) of the most appropriate format.
    '''

    # Get the appropriate format number
    format_selection = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a conversation flow analyst. Select the most appropriate conversation format based on context."},
            {"role": "user", "content": prompt_format_selection}
        ]
    )
    
    try:
        format_number = int(format_selection.choices[0].message.content.strip()) - 1
        chosen_format = format_parts[format_number]
    except (ValueError, IndexError):
        # Fallback to format 1 if there's any error
        chosen_format = format_parts[0]

    prompt = f'''
    You are a npc character in a simulated town.
    Characters in the town:
    - Satoshi, inventor of the Bitcoin.
    - Musk, Elon Musk, the CEO of Tesla, SpaceX, and Neuralink.
    - Pepe, a meme character, live as a shop owner in the town.
    - Popcat, a meme character, a fisherman in the town.
    - Pippin, a meme character, a coffee maker in the town.
        
    You are {npc_name}, {npc_description}.

    Your are talking to {targetNPC if targetNPC else 'someone'}, here is some more information you should know.
        
    Your past memories and experiences:
    {memories_str}
    Your reflection past experiences and events: 
    {reflections_str}
    {finder_instruction}
    Your context now:
    {npc_context}
    
    {special_instruction if special_instruction else ''}

    Your speaking style should follow this format:
    {chosen_format}

    Your tone should be:
    {tone_instructions}

    Here are examples of your speaking style:
    {talk_examples}

    Please keep your response concise, with a maximum of 20 words.

    Output format:
    - {npc_name} talking to <target npc name>, "<your response following the chosen format>"
    '''
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", "content": "You are a great conversationalist who can adapt your speaking style to match different personalities and formats. Follow the given format structure precisely and you say less than 20 words."},
        {"role": "user", "content": prompt}
      ],
      max_tokens=max_tokens
    )
    output = completion.choices[0].message.content

    # Post-process to ensure each part is concise
    parts = output.split('\n')
    concise_output = '\n'.join(part[:20] for part in parts)  # Truncate each part to 20 words

    print("Function: talkToSomeone")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(concise_output)
    print("\n\n")
    return concise_output

def shoudConversationEnd(memories_str, reflections_str, schedule_str, npc_context, npcId, isFinding, targetNPC = None, things_you_say = None, special_instruction = ''):
    
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    npc_way_of_speak= npc['announcements']
    # format_instructions = npc_way_of_speak.get('Format', '')
    tone_instructions = npc_way_of_speak.get('Tone', '')
    # talk_examples = npc_way_of_speak.get('Talk', '')

    recent_schedule_str = onlyMostRecentSchedule(npc_context, schedule_str)

    finder_instruction = ""
    if isFinding:
        finder_instruction = ''' Your calendar of the day, try to follow your schedule, but fill free to adjust to the current situation: 
                            ''' + recent_schedule_str + ''' Try to wrap up the conversation if you need to do other things on your calendar.'''

    prompt = f'''
    You are a npc character in a simulated town.
    Characters in the town:
    - Satoshi, inventor of the Bitcoin.
    - Musk, Elon Musk, the CEO of Tesla, SpaceX, and Neuralink.
    - Pepe, a meme character, live as a shop owner in the town.
    - Popcat, a meme character, a fisherman in the town.
    - Pippin, a meme character, a coffee maker in the town.
        
    You are {npc_name}, {npc_description}.

    Your are talking to {targetNPC if targetNPC else 'someone'}, here is some more information you should know.
        
    Your past memories and experiences:
    {memories_str}
    Your reflection past experiences and events: 
    {reflections_str}
    {finder_instruction}
    Your context now:
    {npc_context}

    You just said:
    {things_you_say}

    Should the conversation end now?
    Respond with 'End the conversation' or 'Continue Conversation'.

    '''
    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", "content": "You are a great schedule planner and instruction giver. You will process the information give to you and give instruction."},
        {"role": "user", "content": prompt}
      ]
    )
    output = completion.choices[0].message.content
    print("Function: shouldConversationEnd")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output


############################################
# Content Generation Functions
############################################

def generateTheme(memories, reflections, npc_context, npc_action, npcId, special_instruction=''):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']

    prompt = f"""
    You are {npc_name}, {npc_description}.

    Your past memeories and experiences:
    {memories}

    Reflections of you:
    {reflections}

    Your current Context:
    {npc_context}

    Your upcoming Action:
    {npc_action}

    You need to say something during the action.

    {special_instruction if special_instruction else ''}

    Choose an intriguing topic for today's discussion, incorporating additional relevant details, adding depth and insight to the conversation.
    If the topic has been covered extensively, provide a fresh perspective or a new angle to explore.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a knowledgeable and inspiring thinker, and you are talking to yourself."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    output = completion.choices[0].message.content
    print("Function: generateTheme")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output


def generate_new_Announcement(memories, reflections, theme, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    npc_way_of_speak = npc['announcements']
    # Extract speaking style instructions from YAML
    # The .get() method works fine for accessing the values, but YAML block indicators ('>')
    # are included in the strings, which could affect prompt formatting
    # .lstrip('> ').strip() removes the YAML block indicator and any extra whitespace
    format_instructions = npc_way_of_speak.get('Format', '').lstrip('> ').strip()
    tone_instructions = npc_way_of_speak.get('Tone', '').lstrip('> ').strip() 
    talk_examples = npc_way_of_speak.get('Talk', '').lstrip('> ').strip()

    prompt = f"""
    You are {npc_name}, {npc_description}.

    Your past memories and experiences:
    {memories}

    Your Reflection on past experiences and events:
    {reflections} 

    This is how you should structure your speech:
    {format_instructions}

    Your tone should be:
    {tone_instructions}

    Here are examples of how you speak:
    {talk_examples}

    Please generate an announcement about this topic: {theme}
    Follow the format instructions carefully, maintaining your unique speaking style and tone.
    Keep each section under 30 words.
    No emojis.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system", 
                "content": "You are a knowledgeable and inspiring thinker, and you are talking to yourself."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    output = completion.choices[0].message.content
    print("Function: generate_new_Announcement")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

def generateMultipleSentencesForAction(memories, reflections, npc_context, npc_action, npcId, special_instruction=''):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    npc_description = npc['description']
    npc_way_of_speak = npc['announcements']
    format_instructions = npc_way_of_speak.get('Format', '').lstrip('> ').strip()
    tone_instructions = npc_way_of_speak.get('Tone', '').lstrip('> ').strip() 
    talk_examples = npc_way_of_speak.get('Talk', '').lstrip('> ').strip()

    prompt = f"""
    You are {npc_name}, {npc_description}.

    Your past memories and experiences:
    {memories}

    Your reflections on past experiences and events:
    {reflections}

    Your current context:
    {npc_context}

    Your current action:
    {npc_action}

    This is how you should structure your speech:
    {format_instructions}

    Your tone should be:
    {tone_instructions}

    Here are examples of how you speak:
    {talk_examples}

    {special_instruction if special_instruction else ''}

    Please generate at least 10 sentences that you would say during this action:
    - One for the beginning of the action
    - Multiple sentences for during the action
    - One for the end of the action

    Follow the format instructions carefully, maintaining your unique speaking style and tone.
    Keep each sentence under 40 words.
    No emojis.
    """

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a knowledgeable and inspiring thinker, and you are talking to yourself."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    output = completion.choices[0].message.content
    print("Function: generateMultipleSentencesForAction")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    return output

############################################
# Instruction Translation Functions
############################################

def isTheInstructionFindingSomeone(instruction_in_human, words_to_say, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    available_actions = npc.get('availableActions', [])
    ava_npc_action = "\n".join(
        f"- {action['actionId']} : {action['actionName']}, {action['description']}."
        for action in available_actions
    )

    prompt = f"""
    You are an instruction translator in a simulated virtual world. Your task is to convert a natural language instruction 
    into a structured JSON format suitable for NPC behavior.

    {npc_name} initiates the action.

    Determine the `actionId` using the action list below.

    ### NPC ID List and Character Names (use `npcId` for the target NPC when needed):
    10006 : Satoshi
    10007 : Popcat
    10008 : Pepe
    10009 : Musk
    10010 : Pippin

    ### Action ID and Corresponding Actions:
    {ava_npc_action}

    Instruction for the NPC:
    {instruction_in_human}

    Tell me if the actionid should be 127? If yes, return "True", if not, return "False". Don't include any other information.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a detailed instruction translator and decision-maker."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    output = completion.choices[0].message.content.strip()
    print("Function: isTheInstructionFindingSomeone")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(output)
    print("\n\n")
    if "True" in output:
        return True
    else:
        return False



def humanInstToJava_action_127(instruction_in_human, words_to_say, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    available_actions = npc.get('availableActions', [])
    ava_npc_action = "\n".join(
        f"- {action['actionId']} : {action['actionName']}, {action['description']}."
        for action in available_actions
        if action['actionId'] == 127
    )

    prompt = f"""
    You are an instruction translator in a simulated virtual world. Your task is to convert a natural language instruction 
    into a structured JSON format suitable for NPC behavior.

    {npc_name} initiates the action.

    ActionId is 127 for finding someone to talk.
    - Use `npcId` for the target NPC being interacted with.

    ### NPC ID and Corresponding Character Names:
    10006 : Satoshi
    10007 : Popcat
    10008 : Pepe
    10009 : Musk
    10010 : Pippin

    ### Action ID and Corresponding Actions:
    {ava_npc_action}

    Instruction for the NPC:
    {instruction_in_human}

    Words to say before the action, during the action, and at the end of the action:
    {words_to_say}

    Please convert the instruction into a structured JSON format with the following fields, ensuring it can be loaded using `json.loads()`:
    {{
        "npcId": {npcId},
        "actionId": 127,
        "data": {{
            "npcId": <target NPC id, 10006 for Satoshi, 10007 for Popcat, 10008 for Pepe, 10009 for Musk, 10010 for Pippin, only the id please>
        }},
        "durationTime": <fill in, action duration time in milliseconds>,
        "speak": [
            <fill in, sentences to say at the beginning of the action>,
            <fill in, sentences to say during the action>,
            ...
            <fill in, sentences to say at the end of the action>
        ]
    }}
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a detailed instruction translator and JSON formatter."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    outputinst = completion.choices[0].message.content
    print("Function: humanInstToJava_action_127")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(outputinst)
    print("\n\n")
    return outputinst


def humanInstToJava_action_other(instruction_in_human, words_to_say, npcId):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    available_actions = npc.get('availableActions', [])
    ava_npc_action = ""
    available_locations = ""
    for action in available_actions:
        if action['actionId'] != 127:
            ava_npc_action += (
                f"- {action['actionId']} : {action['actionName']}, {action['description']}.\n"
            )
        available_locations += f"{action['location']},"

    prompt = f"""
    You are an instruction translator in a simulated virtual world. Your task is to convert a natural language instruction 
    into a structured JSON format suitable for NPC behavior.

    {npc_name} initiates the action.


    ### Action ID and Corresponding Actions:
    {ava_npc_action}

    ### Object ID List as Location(oid),  Use `oid` to indicate the object or location where the action is performed:
    {available_locations}

    Instruction for the NPC:
    {instruction_in_human}

    Words to say before the action, during the action, and at the end of the action:
    {words_to_say}

    Please convert the instruction into a structured JSON format with the following fields, ensuring it can be loaded using `json.loads()`:
    {{
        "npcId": {npcId},
        "actionId": <fill in, the Action Id of what the npc is doing>,
        "data": {{
            "oid": <fill in, the Object ID of where the action is performed, only use the given oid>
        }},
        "durationTime": <fill in, action duration time in milliseconds>,
        "speak": [
            <fill in, sentences to say at the beginning of the action>,
            <fill in, sentences to say during the action>,
            ...
            <fill in, sentences to say during the action>,
            <fill in, sentences to say at the end of the action>
        ]
    }}
    """
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a detailed instruction translator and JSON formatter."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    outputinst = completion.choices[0].message.content
    print("Function: humanInstToJava_action_other")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(outputinst)
    print("\n\n")
    return outputinst


def humanInstToJava_action(instruction_in_human, words_to_say, npcId):
    if isTheInstructionFindingSomeone(instruction_in_human, words_to_say, npcId):
        return humanInstToJava_action_127(instruction_in_human, words_to_say, npcId)
    else:
        return humanInstToJava_action_other(instruction_in_human, words_to_say, npcId)


def humanInstToJava_talk(instruction_in_human, words_to_say, npcId, target_npc_id):
    npc = next((npc for npc in char_config['npcCharacters'] if npc['npcId'] == npcId), None)
    if not npc:
        raise ValueError(f"NPC with npcId {npcId} not found in char_config.yaml")

    npc_name = npc['name']
    available_actions = npc.get('availableActions', [])
    ava_npc_action = ""
    for action in available_actions:
        if action['actionId'] != 127:
            ava_npc_action += (
                f"- {action['actionId']} : {action['actionName']}, {action['description']}.\n"
            )
    available_locations = ",".join(action['location'] for action in available_actions)

    prompt = f"""
    You are an instruction translator in a simulated virtual world. Your task is to convert a natural language instruction 
    into a structured JSON format suitable for NPC behavior.

    {npc_name} talks to someone.

    Follow these steps:
    1. Extract target npcId from the instruction and place it in the `data` field as `npcId`.
    2. Use the provided words to fill in the sentences to say, and place in in the 'data' field as 'content'.
    3. If the conversation is ending, set `endingTalk` to 1.

    ### NPC ID List and Character Names (for npcId field below):
    10006 : Satoshi
    10007 : Popcat
    10008 : Pepe
    10009 : Musk
    10010 : Pippin

    Instruction for the NPC:
    {instruction_in_human}

    Please convert the instruction into a structured JSON format with the following fields, It is very important that your output can be loaded with json.loads().
    Output format:
    {{
        "npcId": {npcId},
        "actionId": 118,
        "data": {{
            "npcId": {target_npc_id if target_npc_id else "<fill in, the npcid of the target npc who will receive the talk message, here is the npc id list 10006 satoshi, 10007 popocat, 10008 pepe, 10009 musk, 10010 pippin>"},
            "content": <fill in, the content of the chat, what the npc says.>,
            "endingTalk" : <fill in 0 or 1, 1 if the npc is ending the conversation now, 0 if continue conversation>
        }},
    }}
    You only give one instruction at a time, not multiple instruction.
    """
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a detailed instruction translator and JSON formatter."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
    )
    outputinst = completion.choices[0].message.content
    print("Function: humanInstToJava_talk")
    print("Prompt:")
    print(prompt)
    print("Output:")
    print(outputinst)
    print("\n\n")
    return outputinst