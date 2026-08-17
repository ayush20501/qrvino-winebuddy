from flask import render_template, request, redirect, Blueprint, session
from app.config import openai, openai_client, create_database_connection, OPENAI_MODEL, OPENAI_WEBSEARCH_MODEL
import re
import os
import logging
import time
import json
customers_bp = Blueprint('customers', __name__)

def parse_sommelier_notes(raw_notes):
    matches = re.findall(r'(?:^|\n)\s*(?:\*\*|\*)?([A-Za-z0-9\s&/\-\'\?]+?)(?:\*\*|\*)?:\s*([\s\S]*?)(?=\s*\n\s*(?:\*\*|\*)?[A-Za-z0-9\s&/\-\'\?]+(?:\*\*|\*)?:\s*|\s*$)', raw_notes)
    return {label.strip(): value.strip("* \t\n\r").replace("\n", "<br>") for label, value in matches}

def make_clickable(match):
        word = match.group(1)
        return f'<a href="#" style="color:yellow" class="highlighted-word" onclick="selectCut(\'{word}\')">{word}</a>'

def slugify(text):
    text = str(text).strip().lower()
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'[^\w\-]+', '', text)
    text = re.sub(r'\-\-+', '-', text)
    return text.strip('-')

def find_customer_by_slug(slug):
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute("SELECT AI_CSTMR_START_TXT FROM ai_cstmr")
        rows = cursor.fetchall()
        for row in rows:
            raw_name = row['AI_CSTMR_START_TXT'].strip()
            if slugify(raw_name) == slug:
                return raw_name
    except Exception as e:
        logging.error(f"Error matching slug: {e}")
    finally:
        cursor.close()
        db_connection.close()
    return None

@customers_bp.route('/chat/<slug>')
def show_image(slug):
    page_name = find_customer_by_slug(slug)
    if not page_name:
        return redirect('/')
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = "SELECT CANA_IND, BEER_IND from ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query,('%' + page_name + '%',))
        result = cursor.fetchone()

        if result is not None and result['CANA_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,RSTRNT_SCAN_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,LOGO_PATH, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                rstrnt_scan_ind = result.get('RSTRNT_SCAN_IND') or 'N'
                prime_ind = result['PRIME_IND']
                logo_path = result['LOGO_PATH']
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})

                if meat_cut_ind == 'Y':
                    second_line_from_database = re.sub(r'\*([^\*]+)\*', make_clickable, second_line_from_database)
                session['theme_color'] = 'Y'
                return render_template('customer_chat.html', logo_path=logo_path, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "Y", options = options_list, rstrnt_ind=rstrnt_ind, rstrnt_scan_ind=rstrnt_scan_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}

        elif result is not None and result['BEER_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,RSTRNT_SCAN_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,LOGO_PATH, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()

            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                rstrnt_scan_ind = result.get('RSTRNT_SCAN_IND') or 'N'
                prime_ind = result['PRIME_IND']
                logo_path = result['LOGO_PATH']
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})

                matches_list = []
                intro_text = ""
                if meat_cut_ind == 'Y':
                    intro_text_match = re.match(r'([^*]+):', second_line_from_database)
                    intro_text = intro_text_match.group(1)+":" if intro_text_match else ""
                    matches_list = re.findall(r'\*([^\*]+)\*', second_line_from_database)

                matches_list = sorted(matches_list)
                session['theme_color'] = 'G'
                return render_template('customer_chat.html',intro_text=intro_text, matches_list = matches_list,logo_path=logo_path, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "G", options = options_list, rstrnt_ind=rstrnt_ind, rstrnt_scan_ind=rstrnt_scan_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}
        else:
            query = "SELECT RSTRNT_IND,RSTRNT_SCAN_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,LOGO_PATH, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                rstrnt_scan_ind = result.get('RSTRNT_SCAN_IND') or 'N'
                prime_ind = result['PRIME_IND']
                logo_path = result['LOGO_PATH']
                first_line = result['CHTBX_FRST_LINE']
                second_line_from_database = result['CHTBX_SCND_LINE']
                ai_cstmr_key = result['AI_CSTMR_KEY']
                session['ai_cstmr_key'] = ai_cstmr_key

                options_list = []
                for i in range(1, 11):
                    opt = result[f'OPTION_{i}_TXT']
                    if opt and opt != 'null' and opt != '':
                        options_list.append({'id': i, 'text': opt})

                query = "SELECT CSTMR_WINE_URL FROM CSTMR_WIN_SELR WHERE AI_CSTMR_KEY = %s"
                cursor.execute(query, (ai_cstmr_key,))
                result = cursor.fetchone()
                image_url = result['CSTMR_WINE_URL']

                if image_url == '' or image_url == 'null':
                    image_url = False

                matches_list = []
                intro_text = ""

                if meat_cut_ind == 'Y':
                    intro_text_match = re.match(r'([^*]+):', second_line_from_database)
                    intro_text = intro_text_match.group(1)+":" if intro_text_match else ""
                    matches_list = re.findall(r'\*([^\*]+)\*', second_line_from_database)
                matches_list = sorted(matches_list)
                session['theme_color'] = 'N'
                return render_template('customer_chat.html',intro_text=intro_text, matches_list = matches_list, ai_cstmr_key = ai_cstmr_key, logo_path=logo_path, image_url = image_url,
                first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "N", options = options_list, rstrnt_ind=rstrnt_ind, rstrnt_scan_ind=rstrnt_scan_ind, prime_ind=prime_ind)
            else:
                return {'page_name': page_name}
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

@customers_bp.route('/customer/scan_bottle', methods=['POST'])
def scan_bottle():
    import base64
    import io
    import requests
    from PIL import Image

    if 'file' not in request.files:
        return {'error': 'No file uploaded'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400

    image_bytes = file.read()
    api_key = os.getenv("VISION_API_KEY")
    if not api_key:
        return {'error': 'VISION_API_KEY not configured'}, 500

    encoded_original = base64.b64encode(image_bytes).decode("utf-8")

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload = {
        "requests": [{
            "image": {"content": encoded_original},
            "features": [{"type": "OBJECT_LOCALIZATION"}]
        }]
    }
    response = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    localization_result = response.json().get("responses", [{}])[0]
    objects = localization_result.get("localizedObjectAnnotations", [])

    if not objects:
        cropped_encoded = encoded_original
    else:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size

        target_object = None
        max_area = 0

        for obj in objects:
            vertices = obj["boundingPoly"]["normalizedVertices"]
            if len(vertices) < 4:
                continue
            xmin = int(vertices[0].get("x", 0) * width)
            ymin = int(vertices[0].get("y", 0) * height)
            xmax = int(vertices[2].get("x", 1) * width)
            ymax = int(vertices[2].get("y", 1) * height)

            obj_width = xmax - xmin
            obj_height = ymax - ymin
            area = obj_width * obj_height

            if area > max_area:
                max_area = area
                target_object = {
                    "box": (xmin, ymin, xmax, ymax),
                    "name": obj["name"]
                }

        if target_object:
            cropped_img = img.crop(target_object["box"])
            cropped_buffer = io.BytesIO()
            cropped_img.save(cropped_buffer, format="JPEG")
            cropped_encoded = base64.b64encode(cropped_buffer.getvalue()).decode("utf-8")
        else:
            cropped_encoded = encoded_original

    payload_text = {
        "requests": [{
            "image": {"content": cropped_encoded},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    response_text = requests.post(url, data=json.dumps(payload_text), headers={"Content-Type": "application/json"})
    text_result = response_text.json().get("responses", [{}])[0]
    text_annotations = text_result.get("textAnnotations", [])

    if not text_annotations:
        return {'name': ''}

    raw_text = text_annotations[0]["description"]

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        response_openai = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a wine and beer expert. Extract the brand/producer and the product/varietal name from the OCR text. Follow these rules:\n1. Remove all extraneous information like locations, vintage years, alcohol content, volumes, importer/exporter names, warnings, and single letters.\n2. Do not omit words that are part of the brand name (e.g., 'Yes Way Rosé', not 'Way Rosé').\n3. Autocorrect obvious OCR spelling typos of wine/beer terms (e.g., convert 'Frenache' to 'Grenache', 'Grald' to 'Gerald').\n4. Format the final output in Title Case (e.g., 'Domaine Talmard Macon-Chardonnay' instead of all caps).\n5. Return ONLY the clean, corrected name. If no clear wine/beer name is found, return the input text cleaned in Title Case."},
                {"role": "user", "content": f"OCR Text:\n{raw_text}"}
            ],
            temperature=0.0
        )
        cleaned_name = response_openai.choices[0].message.content.strip()
    except Exception as e:
        cleaned_name = raw_text

    return {'name': cleaned_name}

@customers_bp.route('/customer/scan_menu', methods=['POST'])
def scan_menu():
    import base64
    import io
    import requests
    from PIL import Image

    if 'file' not in request.files:
        return {'error': 'No file uploaded'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No file selected'}, 400

    scan_type = request.form.get('scan_type', 'food')

    image_bytes = file.read()
    api_key = os.getenv("VISION_API_KEY")
    if not api_key:
        return {'error': 'VISION_API_KEY not configured'}, 500

    encoded_original = base64.b64encode(image_bytes).decode("utf-8")
    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    payload_text = {
        "requests": [{
            "image": {"content": encoded_original},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    response_text = requests.post(url, data=json.dumps(payload_text), headers={"Content-Type": "application/json"})
    text_result = response_text.json().get("responses", [{}])[0]
    text_annotations = text_result.get("textAnnotations", [])

    if not text_annotations:
        return {'items': []}

    raw_text = text_annotations[0]["description"]

    try:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if scan_type == 'wine':
            prompt_instr = (
                "You are an expert sommelier. Extract all individual wine items/names from the following OCR text of a wine list menu.\n"
                "Return a JSON object with a single key 'items' containing a list of cleaned wine item strings.\n"
                "Do not include section headings or non-wine items.\n"
                "Example format: {\"items\": [\"Roseblood d'Estoublon, Rosé, Coteaux Varois en Provence, 2025\", \"Cobb, 'MesFilles,' Chardonnay, Sonoma Coast, 2022\"]}"
            )
        else:
            prompt_instr = (
                "You are a food and restaurant expert. Extract all individual food dish items from the following OCR text of a restaurant food menu.\n"
                "Return a JSON object with a single key 'items' containing a list of cleaned dish name strings.\n"
                "Do not include section headings, prices, or descriptions unless necessary to identify the dish.\n"
                "Example format: {\"items\": [\"Crispy Brick Chicken\", \"Double Cut Lamb Chops\", \"16oz Double Wagyu Cheeseburger\"]}"
            )

        response_openai = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt_instr},
                {"role": "user", "content": f"OCR Text:\n{raw_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        res_json = json.loads(response_openai.choices[0].message.content.strip())
        items = res_json.get("items", [])
    except Exception as e:
        items = [line.strip() for line in raw_text.split('\n') if len(line.strip()) > 3]

    return {'items': items}

@customers_bp.route('/customer/palate', methods=['GET', 'POST'])
def show_palate_questionnaire():
    if request.method == 'GET':
        return redirect('/')
    user_input = request.form.get("user_input", "")
    wine_option = request.form.get("wine_option", "1")
    customer_name = request.form.get("customer_name", "")
    wine_name = request.form.get("wine_name", "")
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True, buffered=True)
    try:
        query = "SELECT LOGO_PATH, BEER_IND, CANA_IND FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        cstmr = cursor.fetchone()
        is_beer = False
        if cstmr and cstmr['BEER_IND'] == 'Y':
            is_beer = True
        if is_beer:
            cursor.execute("SELECT * FROM Palate_Type WHERE Actv_Ind = 'Y' AND BEER_IND = 'Y' ORDER BY `id` ASC")
            palate_types = cursor.fetchall()
            cursor.execute("SELECT * FROM Palate WHERE Actv_Ind = 'Y' AND BEER_IND = 'Y'")
            palates = cursor.fetchall()
        else:
            cursor.execute("SELECT * FROM Palate_Type WHERE Actv_Ind = 'Y' AND (BEER_IND IS NULL OR BEER_IND != 'Y') ORDER BY `id` ASC")
            palate_types = cursor.fetchall()
            cursor.execute("SELECT * FROM Palate WHERE Actv_Ind = 'Y' AND (BEER_IND IS NULL OR BEER_IND != 'Y')")
            palates = cursor.fetchall()
        palate_map = {}
        for p in palates:
            pt_id = p['Palate_Type_Id']
            if pt_id not in palate_map:
                palate_map[pt_id] = []
            palate_map[pt_id].append(p)
        questions = []
        for pt in palate_types:
            options = palate_map.get(pt['id'], [])
            if options:
                questions.append({
                    'id': pt['id'],
                    'name': pt['Name'],
                    'options': options
                })
        if not questions:
            return get_customer_recommendations()
        logo_path = cstmr['LOGO_PATH'] if cstmr else None
        theme_color = 'N'
        if cstmr:
            if cstmr['BEER_IND'] == 'Y':
                theme_color = 'G'
            elif cstmr['CANA_IND'] == 'Y':
                theme_color = 'Y'
        return render_template('customer_palate.html',
                               questions=questions,
                               user_input=user_input,
                               wine_option=wine_option,
                               customer_name=customer_name,
                               wine_name=wine_name,
                               logo_path=logo_path,
                               color=theme_color)
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        cursor.close()
        db_connection.close()

@customers_bp.route('/customer/recommendations', methods=['POST'])
def get_customer_recommendations():
    db_connection = None
    cursor = None
    try:
        link_exists = False
        link_reg_exists = False
        both_links_exist = False
        myflag=0
        cl=None
        user_input = request.form.get("user_input")
        wine_option = request.form.get('wine_option')
        customer_name = request.form.get('customer_name')
        if not wine_option or not str(wine_option).isdigit() or not (1 <= int(wine_option) <= 10):
            wine_option = "1"
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        prompt_column = f"PROMPT_TXT_{wine_option}"
        query = f"SELECT BEER_IND, RSTRNT_IND, RSTRNT_SCAN_IND, WINE_FOOD_PAIR_TXT, NO_WINE_BEER_IND, {prompt_column} FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        cstmr_result = cursor.fetchone()
        is_beer = False
        if cstmr_result and cstmr_result['BEER_IND'] == 'Y':
            is_beer = True
        if is_beer:
            cursor.execute("SELECT * FROM Palate_Type WHERE Actv_Ind = 'Y' AND BEER_IND = 'Y' ORDER BY `id` ASC")
        else:
            cursor.execute("SELECT * FROM Palate_Type WHERE Actv_Ind = 'Y' AND (BEER_IND IS NULL OR BEER_IND != 'Y') ORDER BY `id` ASC")
        palate_types = cursor.fetchall()
        gender_desc = ""
        other_descs = []
        for pt in palate_types:
            ans_id = request.form.get(f"palate_q_{pt['id']}")
            if ans_id:
                cursor.execute("SELECT Description FROM Palate WHERE id = %s", (ans_id,))
                opt_row = cursor.fetchone()
                if opt_row:
                    desc = opt_row['Description'].strip()
                    if pt['Name'].strip().lower() == 'gender':
                        gender_desc = desc
                    else:
                        other_descs.append(desc)
        palate_prefix = ""
        if gender_desc and other_descs:
            palate_prefix = f"I'm {gender_desc},, I like: {', '.join(other_descs)}.. .."
        elif gender_desc:
            palate_prefix = f"I'm {gender_desc}.. .."
        elif other_descs:
            palate_prefix = f"I like: {', '.join(other_descs)}.. .."
        rstrnt_ind = cstmr_result['RSTRNT_IND'] if cstmr_result else 'N'
        no_wine_beer_ind = cstmr_result['NO_WINE_BEER_IND'] if cstmr_result else 'N'
        rstrnt_scan_ind = cstmr_result.get('RSTRNT_SCAN_IND') or 'N' if cstmr_result else 'N'
        wine_name = request.form.get("wine_name", "").strip()

        is_scanned_pairing = False
        if rstrnt_scan_ind == 'Y' and wine_name:
            is_scanned_pairing = True
            prompt_template = cstmr_result.get('WINE_FOOD_PAIR_TXT') or ""
            prompt_result = prompt_template.replace("the entered wine", wine_name).replace("the entered beer", wine_name)
        else:
            prompt_result = str(cstmr_result[prompt_column]) if (cstmr_result and cstmr_result[prompt_column]) else ""
            if palate_prefix:
                prompt_result = palate_prefix + " " + prompt_result

        theme_color = session.get('theme_color', 'N')

        if "[WEB_SEARCH]" in prompt_result:
            clean_prompt = prompt_result.replace("[WEB_SEARCH]", "").strip()
            if user_input:
                for placeholder in ["{user_input}", "{food}", "{dish}", "{item}", "the entered food", "the entered dish", "the entered wine", "the entered item"]:
                    if placeholder in clean_prompt:
                        clean_prompt = clean_prompt.replace(placeholder, user_input)
                        break
                else:
                    clean_prompt = f"{clean_prompt}? {user_input}"
            chatbot_response = get_websearch_response(clean_prompt)
            if not chatbot_response:
                return "No response from chatbot"
            is_table, rendered_content = format_websearch_output(chatbot_response)
            if is_table:
                return render_template("recommendations_table.html", token=1, var=rendered_content, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)
            else:
                return render_template("recommendations_table.html", paragraphs_with_links=rendered_content, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)

        if is_scanned_pairing:
            system_role = "You are BeerBuddy, an elite virtual cicerone." if cstmr_result.get('BEER_IND') == 'Y' else "You are WineBuddy, an elite virtual sommelier."
            conversation = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt_result}
            ]
            chatbot_response = get_chatbot_response(conversation)
            if chatbot_response:
                matched_varietals = []
                cursor.execute("SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl")
                matched_varietals = cursor.fetchall()
                formatted_response = chatbot_response
                for varietal, varietal_key in matched_varietals:
                    varietal_link = f'<a href="/customer/stores?key={varietal_key}">{varietal}</a>'
                    formatted_response = formatted_response.replace(varietal, varietal_link, 1)
                formatted_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', formatted_response)
                paragraphs = formatted_response.split('\n\n')
                paragraphs_with_links = []
                for p in paragraphs:
                    p_formatted = p.replace('\n', '<br>')
                    paragraphs_with_links.append(p_formatted)
                return render_template("recommendations_table.html", paragraphs_with_links=paragraphs_with_links, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=session.get('theme_color', 'N'))
            else:
                return "No response from chatbot"

        if theme_color == 'G':
            beer_pairings = get_beer_pairings(prompt_result, user_input)
            if not beer_pairings:
                return "No response from chatbot"
            cursor.execute("SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl")
            beer_varietals = cursor.fetchall()
            parsed_pairings = []
            headers_set = []
            for p in beer_pairings:
                raw_notes = p.get("sommelier_notes", "")
                parsed_notes = parse_sommelier_notes(raw_notes)
                parsed_pairings.append({
                    "name": (p.get("name") or "").strip(),
                    "notes": parsed_notes
                })
                for label in parsed_notes.keys():
                    if label not in headers_set:
                        headers_set.append(label)
            headers = ["Varietal"] + headers_set
            html_table = "<table>\n<thead>\n" + "".join(f"<th>{h}</th>\n" for h in headers) + "\n</thead><tbody>\n"
            for p in parsed_pairings:
                name = p["name"]
                matched = next((item for item in beer_varietals if item['VRTL_NM'].strip().lower() == name.lower()), None)
                name_cell = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag=1">{matched["VRTL_NM"]}</a>' if matched else name
                row_cells = [f'<td data-label="Varietal">{name_cell}</td>']
                for header in headers_set:
                    val = p["notes"].get(header, "")
                    row_cells.append(f'<td data-label="{header}">{val}</td>')
                html_table += "<tr>\n" + "".join(row_cells) + "\n</tr>\n"
            html_table += "</tbody>\n</table>"
            return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)

        if theme_color == 'N':
            wine_pairings = get_wine_pairings(prompt_result, user_input)
            if not wine_pairings:
                return "No response from chatbot"
            cursor.execute("SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl")
            wine_varietals = cursor.fetchall()
            parsed_pairings = []
            headers_set = []
            for p in wine_pairings:
                raw_notes = p.get("sommelier_notes", "")
                parsed_notes = parse_sommelier_notes(raw_notes)
                parsed_pairings.append({
                    "name": (p.get("name") or "").strip(),
                    "notes": parsed_notes
                })
                for label in parsed_notes.keys():
                    if label not in headers_set:
                        headers_set.append(label)
            headers = ["Varietal"] + headers_set
            html_table = "<table>\n<thead>\n" + "".join(f"<th>{h}</th>\n" for h in headers) + "\n</thead><tbody>\n"
            for p in parsed_pairings:
                name = p["name"]
                matched = next((item for item in wine_varietals if item['VRTL_NM'].strip().lower() == name.lower()), None)
                name_cell = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag=1">{matched["VRTL_NM"]}</a>' if matched else name
                row_cells = [f'<td data-label="Varietal">{name_cell}</td>']
                for header in headers_set:
                    val = p["notes"].get(header, "")
                    row_cells.append(f'<td data-label="{header}">{val}</td>')
                html_table += "<tr>\n" + "".join(row_cells) + "\n</tr>\n"
            html_table += "</tbody>\n</table>"
            return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=theme_color)

        table_instruction = ("Please return response in tabular format with exactly 5 columns: "
                             "Wine Style Name | Flavor Profile | Pairing Notes | Best Glass | Best Serving Temperature. "
                             "Flavor Profile column: Flavor: <value>, Aroma: <value>, Tannins: <value>, Taste: <value>, ABV: <value>. "
                             "Pairing Notes column: 2-3 sentences explaining why this wine pairs well with the dish. "
                             "Best Glass column: only the glass type. "
                             "Best Serving Temperature column: only the serving temperature.")

        conversation = [
            {"role": "system", "content": "You are WineBuddy and BeerBuddy the Virtual Sommelier for wine and beer. You can recommend wine or beer as asked. " + table_instruction},
            {"role": "user", "content": f'{prompt_result}? {user_input}'},
        ]
        chatbot_response = get_chatbot_response(conversation)
        matched_varietals = []
        query = "SELECT VRTL_NM,VRTL_KEY FROM ai_vrtl"
        cursor.execute(query)
        matched_varietals = cursor.fetchall()
        matched_regions = []
        query = "SELECT CNTRGN_KEY,CNTRGN_NM FROM CNTRGN"
        cursor.execute(query)
        matched_regions = cursor.fetchall()
        if chatbot_response is not None:
            matched_column_no = None
            tabular_pattern = re.compile(r'\|')
            if tabular_pattern.search(chatbot_response):
                lines = chatbot_response.strip().split('\n')
                start_index = next((index for index, line in enumerate(lines) if '|' in line), None)
                if start_index is not None:
                    headers = [header.strip() for header in lines[start_index].split('|') if header.strip()]
                    data_lines = [line.strip() for line in lines[start_index + 2:]]
                    target_words = ["regions", "countries", "regions/countries","countries/regions"]
                    for i, header in enumerate(headers, 1):
                        for word in target_words:
                            if word in header.lower():
                                matched_column_no = i
                                break
                        if matched_column_no is not None:
                            cl=matched_column_no-1
                            break
                html_table = "<table>\n<thead>\n"
                html_table += "".join([f"<th>{header}</th>\n" for header in headers])
                html_table += "\n</thead><tbody>\n"

                for line in data_lines:
                    if '---' in line:
                        continue
                    columns = [column.strip() for column in line.split('|') if column.strip()]
                    if len(columns)<=0:
                        break
                    if columns and columns[0]:
                        matched = next((item for item in matched_varietals if item['VRTL_NM'].strip().lower() == columns[0].strip().lower()), None)
                        if matched:
                            link_exists = True
                            myflag=1
                            link = f'<a href="/customer/stores?key={matched["VRTL_KEY"]}&testflag={myflag}">{matched["VRTL_NM"]}</a>'
                            columns[0] = link
                    if cl is not None :
                        column_words_processed = [(word.split('(')[0].replace(" ", "").lower().strip() if '(' in word else word.replace(" ", "").lower().strip())
                        for word in columns[matched_column_no - 1].split(',')]
                        matched_reg = next((itemreg for itemreg in matched_regions if any(word in itemreg['CNTRGN_NM'].replace(" ", "").lower().strip() for word in column_words_processed)), None)
                        if matched_reg:
                            link_reg_exists = True
                            if link_exists and link_reg_exists:
                                myflag=3
                            link_reg = f'<a href="/customer/stores?testflag={myflag}&vrtlkey={matched["VRTL_KEY"]}&keyreg={matched_reg["CNTRGN_KEY"]}">{matched_reg["CNTRGN_NM"]}</a>'
                            columns[matched_column_no-1] = link_reg
                    html_table += "<tr>\n"
                    html_table += "".join([f"<td>{column}</td>\n" for column in columns])
                    html_table += "</tr>\n"
                html_table += "</tbody>\n</table>"
                return render_template("recommendations_table.html", token=1, var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=session.get('theme_color', 'N'))
            else:
                formatted_response = chatbot_response
                for varietal, varietal_key in matched_varietals:
                    varietal_link = f'<a href="/customer/stores?key={varietal_key}">{varietal}</a>'
                    formatted_response = formatted_response.replace(varietal, varietal_link, 1)
                paragraphs_with_links = formatted_response.split('\n\n')
                return render_template("recommendations_table.html", paragraphs_with_links=paragraphs_with_links, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind, color=session.get('theme_color', 'N'))
        else:
            return "No response from chatbot"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()

def get_chatbot_response(messages):
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0
            )
            return response.choices[0].message["content"]
        except Exception as e:
            logging.error(f"OpenAI attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def get_websearch_response(prompt_text):
    for attempt in range(3):
        try:
            response = openai_client.responses.create(
                model=OPENAI_WEBSEARCH_MODEL,
                tools=[{"type": "web_search"}],
                input=prompt_text
            )
            output = getattr(response, "output_text", None)
            if not output and hasattr(response, "output"):
                output = str(response.output)
            if output:
                return output
        except Exception as e:
            logging.error(f"OpenAI web search attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def format_websearch_output(markdown_text):
    if not markdown_text:
        return False, []
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', markdown_text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    table_lines = [line for line in lines if '|' in line]
    if len(table_lines) >= 2:
        headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
        data_start = 1
        if len(table_lines) > 1 and all(c in '-: |' for c in table_lines[1]):
            data_start = 2
        html_table = "<table>\n<thead>\n<tr>\n"
        html_table += "".join([f"<th>{h}</th>\n" for h in headers])
        html_table += "</tr>\n</thead>\n<tbody>\n"
        for line in table_lines[data_start:]:
            if all(c in '-: |' for c in line):
                continue
            cols = [col.strip() for col in line.split('|')]
            if line.startswith('|'):
                cols = cols[1:]
            if line.endswith('|'):
                cols = cols[:-1]
            if not cols or all(not c for c in cols):
                continue
            html_table += "<tr>\n"
            for idx, col in enumerate(cols):
                header_name = headers[idx] if idx < len(headers) else ""
                html_table += f'<td data-label="{header_name}">{col}</td>\n'
            html_table += "</tr>\n"
        html_table += "</tbody>\n</table>"
        return True, html_table
    else:
        paragraphs = text.split('\n\n')
        formatted_paragraphs = [p.replace('\n', '<br>') for p in paragraphs if p.strip()]
        return False, formatted_paragraphs

def get_beer_pairings(prompt_result, user_input):
    functions = [{
        "name": "return_beer_pairings",
        "description": "Return a list of beer pairing recommendations for the requested dish.",
        "parameters": {
            "type": "object",
            "properties": {
                "pairings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Beer style, brand or variety name"},
                            "sommelier_notes": {
                                "type": "string",
                                "description": "Sommelier notes about the beer. You must strictly follow the user's prompt instructions for what details to include, formatting each detail/field label in bold and on a new line using markdown format (e.g., '**Label:** Value\\n')."
                            }
                        },
                        "required": ["name", "sommelier_notes"]
                    }
                }
            },
            "required": ["pairings"]
        }
    }]
    messages = [
        {"role": "system", "content": (
            "You are BeerBuddy, an expert virtual beer sommelier. Recommend suitable beers and strictly return them using the return_beer_pairings function. "
            "CRITICAL RULES FOR 'sommelier_notes': You must dynamically identify every specific detail requested by the user prompt. "
            "You are strictly forbidden from grouping multiple details into a single paragraph. "
            "You must format the notes as a strict vertical list where each requested detail is on its own separate new line (\\n). "
            "Every field label you extract must be strictly wrapped in double asterisks followed by a colon and a space. "
            "For example, if the user asks for origin and taste, output exactly: '**Origin:** [value]\\n**Taste:** [value]'. "
            "If they ask for grape and body, output exactly: '**Grape:** [value]\\n**Body:** [value]'. "
            "Failure to follow this exact bolded, line-by-line format will result in a system error."
        )},
        {"role": "user", "content": f'{prompt_result}? {user_input}'}
    ]
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                functions=functions,
                function_call={"name": "return_beer_pairings"},
                temperature=0
            )
            arguments = response.choices[0].message["function_call"]["arguments"]
            return json.loads(arguments).get("pairings", [])
        except Exception as e:
            logging.error(f"OpenAI beer attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def get_wine_pairings(prompt_result, user_input):
    functions = [{
        "name": "return_wine_pairings",
        "description": "Return a list of wine pairing recommendations for the requested dish.",
        "parameters": {
            "type": "object",
            "properties": {
                "pairings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Wine style, varietal or brand name"},
                            "sommelier_notes": {
                                "type": "string",
                                "description": "Sommelier notes about the wine. You must strictly follow the user's prompt instructions for what details to include, formatting each detail/field label in bold and on a new line using markdown format (e.g., '**Label:** Value\\n')."
                            }
                        },
                        "required": ["name", "sommelier_notes"]
                    }
                }
            },
            "required": ["pairings"]
        }
    }]
    messages = [
        {"role": "system", "content": (
            "You are WineBuddy, an expert virtual wine sommelier. Recommend suitable wines and strictly return them using the return_wine_pairings function. "
            "CRITICAL RULES FOR 'sommelier_notes': You must dynamically identify every specific detail requested by the user prompt. "
            "You are strictly forbidden from grouping multiple details into a single paragraph. "
            "You must format the notes as a strict vertical list where each requested detail is on its own separate new line (\\n). "
            "Every field label you extract must be strictly wrapped in double asterisks followed by a colon and a space. "
            "For example, if the user asks for origin and taste, output exactly: '**Origin:** [value]\\n**Taste:** [value]'. "
            "If they ask for grape and body, output exactly: '**Grape:** [value]\\n**Body:** [value]'. "
            "Failure to follow this exact bolded, line-by-line format will result in a system error."
        )},
        {"role": "user", "content": f'{prompt_result}? {user_input}'}
    ]
    for attempt in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                functions=functions,
                function_call={"name": "return_wine_pairings"},
                temperature=0
            )
            arguments = response.choices[0].message["function_call"]["arguments"]
            return json.loads(arguments).get("pairings", [])
        except Exception as e:
            logging.error(f"OpenAI wine attempt {attempt + 1} failed: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(1)
    return None

def _store_selection_template():
    return "store_selection_modal.html" if request.args.get("modal") == "1" else "store_selection.html"

@customers_bp.route('/customer/stores')
def show_customer_stores():
    testflag = request.args.get("testflag")
    db_connection = None
    cursor = None
    if testflag == "3":
        if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error1: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
        else:
            ai_reg_key = request.args.get("keyreg")
            aivrtlkey = request.args.get("vrtlkey")
            session['ai_reg_key'] = ai_reg_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants,reg_key=ai_reg_key,vrtl=aivrtlkey)
            except Exception as e:
                return f"Error2: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
    elif testflag == "1":
       if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True, buffered=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template(_store_selection_template(), restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error3: {str(e)}"
            finally:
                if cursor:
                    cursor.close()
                if db_connection:
                    db_connection.close()
    else:
        return"There is no match wine seller"

def get_target_url(restaurant_key, vrtl_key):
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """
            SELECT AFLT_VTRL_URL FROM aflt_vtrl_url
            WHERE WINE_SELR_KEY = %s AND VRTL_KEY = %s
            """
        cursor.execute(query, (restaurant_key, vrtl_key))
        url_result = cursor.fetchone()
        if url_result:
            return url_result["AFLT_VTRL_URL"]
    except Exception as e:
        logging.error(f"Error in get_target_url: {e}")
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
    return False

def get_target_url_reg(restaurant_key,reg_key,vrtl):
    db_connection = None
    cursor = None
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True, buffered=True)
        query = """
            SELECT AFLT_VTRL_URL_TXT FROM AFLT_CNTRGN_URL
            WHERE WINE_SELR_KEY = %s AND CNTRGN_KEY = %s AND VRTL_KEY = %s
            """
        cursor.execute(query, (restaurant_key, reg_key,vrtl))
        url_result = cursor.fetchone()
        if url_result:
            return url_result["AFLT_VTRL_URL_TXT"]
    except Exception as e:
        logging.error(f"Error in get_target_url_reg: {e}")
    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
    return False
