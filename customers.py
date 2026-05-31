from flask import Flask, render_template, request,redirect,g,Blueprint,session
from config_db import openai, create_database_connection
import re
import mysql.connector
from bs4 import BeautifulSoup
import os
import logging
import base64

customers_bp = Blueprint('customers', __name__)

def make_clickable(match):
        word = match.group(1)
        return f'<a href="#" style="color:yellow" class="highlighted-word" onclick="selectCut(\'{word}\')">{word}</a>'

@customers_bp.route('/<page_name>')
def show_image(page_name):
    try:
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True)
        query = "SELECT CANA_IND, BEER_IND from ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query,('%' + page_name + '%',))
        result = cursor.fetchone()


        if result != None and result['CANA_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
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
                cursor.close()
                return render_template('aiCustomers.html', image_data=image_data_base64, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "Y", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
            else:
                cursor.close()
                return {'page_name': page_name}

        if result != None and result['BEER_IND'] == 'Y':
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()

            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
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
                return render_template('aiCustomers.html',intro_text=intro_text, matches_list = matches_list,image_data=image_data_base64, first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "G", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
        else:
            query = "SELECT RSTRNT_IND,MEAT_CUT_IND,PRIME_IND,AI_CSTMR_KEY,CHTBX_LOGO_IMG, CHTBX_FRST_LINE, CHTBX_SCND_LINE, OPTION_1_TXT, OPTION_2_TXT, OPTION_3_TXT, OPTION_4_TXT, OPTION_5_TXT, OPTION_6_TXT, OPTION_7_TXT, OPTION_8_TXT, OPTION_9_TXT, OPTION_10_TXT FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
            cursor.execute(query,('%' + page_name + '%',))
            result = cursor.fetchone()
            if result is not None:
                meat_cut_ind = result['MEAT_CUT_IND']
                rstrnt_ind = result['RSTRNT_IND']
                prime_ind = result['PRIME_IND']
                image_data = result['CHTBX_LOGO_IMG']
                image_data_base64 = base64.b64encode(image_data).decode('utf-8') if image_data else ""
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
                return render_template('aiCustomers.html',intro_text=intro_text, matches_list = matches_list, ai_cstmr_key = ai_cstmr_key, image_data=image_data_base64,image_url = image_url,
                first_line=first_line, second_line=second_line_from_database,customer_name=page_name, color = "N", options = options_list, rstrnt_ind=rstrnt_ind, prime_ind=prime_ind)
            else:
                cursor.close()
                return {'page_name': page_name}
    except Exception as e:
        return f"Error: {str(e)}"

def get_chatbot_response(messages):
    response =openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=messages
    )
    return response.choices[0].message["content"]

@customers_bp.route('/chatGPT_response_table', methods=['POST'])
def chatGPT_response_table():
    try:
        link_exists = False
        link_reg_exists = False
        both_links_exist = False
        myflag=0
        cl=None
        user_input = request.form.get("user_input")
        wine_option = request.form.get('wine_option')
        customer_name = request.form.get('customer_name')
        db_connection = create_database_connection()
        cursor = db_connection.cursor(dictionary=True)

        query = "SELECT RSTRNT_IND, NO_WINE_BEER_IND FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        rstrnt_result = cursor.fetchone()
        rstrnt_ind = rstrnt_result['RSTRNT_IND'] if rstrnt_result else 'N'
        no_wine_beer_ind = rstrnt_result['NO_WINE_BEER_IND'] if rstrnt_result else 'N'

        prompt_column = f"PROMPT_TXT_{wine_option}"
        query = f"SELECT {prompt_column} FROM ai_cstmr WHERE AI_CSTMR_START_TXT LIKE %s"
        cursor.execute(query, ('%' + customer_name + '%',))
        cstmr_result = cursor.fetchone()
        prompt_result = str(cstmr_result[prompt_column]) if cstmr_result else ""

        conversation = [
            {"role": "system", "content": "You are WineBuddy,and BeerBudy the Virtual Sommelier for wine and beer.You can recommend wine or beer as asked"},
            {"role": "system", "content": f'{prompt_result}? {user_input} also Please return response in tabular format'},
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
                    data_lines = [line.strip() for line in lines[start_index + 2:-1]]
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
                            link = f'<a href="/restaurants?key={matched["VRTL_KEY"]}&testflag={myflag}">{matched["VRTL_NM"]}</a>'
                            columns[0] = link
                    if cl is not None :
                        column_words_processed = [(word.split('(')[0].replace(" ", "").lower().strip() if '(' in word else word.replace(" ", "").lower().strip())
                        for word in columns[matched_column_no - 1].split(',')]
                        matched_reg = next((itemreg for itemreg in matched_regions if any(word in itemreg['CNTRGN_NM'].replace(" ", "").lower().strip() for word in column_words_processed)), None)
                        if matched_reg:
                            link_reg_exists = True
                            if link_exists and link_reg_exists:
                                myflag=3
                            link_reg = f'<a href="/restaurants?testflag={myflag}&vrtlkey={matched["VRTL_KEY"]}&keyreg={matched_reg["CNTRGN_KEY"]}">{matched_reg["CNTRGN_NM"]}</a>'
                            columns[matched_column_no-1] = link_reg
                    html_table += "<tr>\n"
                    html_table += "".join([f"<td>{column}</td>\n" for column in columns])
                    html_table += "</tr>\n"
                html_table += "</tbody>\n</table>"
                return render_template("chatGPT_response_table.html", token=1,var=html_table, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind)
            else:
                formatted_response = chatbot_response
                for varietal, varietal_key in matched_varietals:
                    varietal_link = f'<a href="/restaurants?key={varietal_key}">{varietal}</a>'
                    formatted_response = formatted_response.replace(varietal, varietal_link, 1)
                paragraphs_with_links = formatted_response.split('\n\n')
                return render_template("chatGPT_response_table.html",paragraphs_with_links=paragraphs_with_links, rstrnt_ind=rstrnt_ind, no_wine_beer_ind=no_wine_beer_ind)
        else:
            return "No response from chatbot"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        cursor.close()
        db_connection.close()

@customers_bp.route('/restaurants')
def restaurants():
    testflag = request.args.get("testflag")
    if testflag == "3":
        if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                selr_key=[]
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template("restaurants.html", restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error1: {str(e)}"
            finally:
                cursor.close()
                db_connection.close()
        else:
            ai_reg_key = request.args.get("keyreg")
            aivrtlkey = request.args.get("vrtlkey")
            session['ai_reg_key'] = ai_reg_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                selr_key_reg=[]
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template("restaurants.html", restr=restaurants,reg_key=ai_reg_key,vrtl=aivrtlkey)
            except Exception as e:
                return f"Error2: {str(e)}"
            finally:
                cursor.close()
                db_connection.close()
    elif testflag == "1":
       if 'key' in request.args:
            ai_vrtl_key = request.args.get("key")
            session['ai_vrtl_key'] = ai_vrtl_key
            cstmr_key=session.get('ai_cstmr_key')
            try:
                selr_key=[]
                db_connection = create_database_connection()
                cursor = db_connection.cursor(dictionary=True)
                query="""SELECT distinct WINE_SELR.* FROM CSTMR_WIN_SELR JOIN ai_cstmr ON CSTMR_WIN_SELR.AI_CSTMR_KEY = ai_cstmr.AI_CSTMR_KEY JOIN WINE_SELR ON CSTMR_WIN_SELR.WIN_SELR_KEY = WINE_SELR.WINE_SELR_KEY WHERE ai_cstmr.AI_CSTMR_KEY = %s AND CSTMR_WIN_SELR.ChatGPT_ACTV_IND = 'Y'"""
                cursor.execute(query, (cstmr_key,))
                restaurants = cursor.fetchall()
                return render_template("restaurants.html", restr=restaurants, vrtl_key=ai_vrtl_key)
            except Exception as e:
                return f"Error3: {str(e)}"
            finally:
                cursor.close()
                db_connection.close()
    else:
        return"There is no match wine seller"

@customers_bp.route("/external_URL", methods=["GET", "POST"])
def external_URL():
    if request.method == "POST":
        selected_restaurant_key = request.form.get("selected_restaurant")
        vrtl_key = request.form.get('vrtlkey')
        reg_key = request.form.get('regkey')
        if vrtl_key and reg_key:
            target_url = get_target_url_reg(selected_restaurant_key,reg_key,vrtl_key)
        else:
            target_url = get_target_url(selected_restaurant_key,vrtl_key)
        if target_url:
            return redirect(target_url)
        else:
            return """
                <html>
                <head>
                    <script>
                        alert("Target URL not found");
                        window.location.href = "/restaurants";
                    </script>
                </head>
                <body>
                    <p>If you are not redirected, <a href="/restaurants">click here</a>.</p>
                </body>
                </html>
            """, 404
    else:
        return "Invalid request method", 405

def get_target_url(restaurant_key, vrtl_key):
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True)
    query = """
        SELECT AFLT_VTRL_URL FROM aflt_vtrl_url
        WHERE WINE_SELR_KEY = %s AND VRTL_KEY = %s
        """
    cursor.execute(query, (restaurant_key, vrtl_key))
    url_result = cursor.fetchone()
    if url_result:
        return url_result["AFLT_VTRL_URL"]
    else:
        return False

def get_target_url_reg(restaurant_key,reg_key,vrtl):
    db_connection = create_database_connection()
    cursor = db_connection.cursor(dictionary=True)
    query = """
        SELECT AFLT_VTRL_URL_TXT FROM AFLT_CNTRGN_URL
        WHERE WINE_SELR_KEY = %s AND CNTRGN_KEY = %s AND VRTL_KEY = %s
        """
    cursor.execute(query, (restaurant_key, reg_key,vrtl))
    url_result = cursor.fetchone()
    if url_result:
        return url_result["AFLT_VTRL_URL_TXT"]
    else:
        return False
