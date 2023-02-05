import pyodbc
from _thread import *
import socket

index = open("index.html", 'r')

parts = index.read().split("<!--CUT_HERE-->")
HTML_BEGIN, HTML_END = parts[0], parts[2]

HTTP_VER = "HTTP/1.0 "
STATUS_OK = "200 OK"

server_name = input("Enter server name (You can find server name by running query 'SELECT @@SERVERNAME')\n")


def create_form(title, table_name, columns, f_type):
    # Creates HTML input form made out of columns of the given table


    html_start = """<div class="card" style="float:left; margin-right:30px;">
                              <h5 class="card-header">%s %s</h5>
                              <div class="card-body">
                                <form action="/%s%s" method="GET">
           """ % (f_type, title, f_type, table_name)
    for i in columns:
        if table_name == "employee" and i == "Age":
            continue

        html_start += """<label style="font-size:15px;" class="mb-2">%s</label><br>
            <input style="padding:4px; margin-bottom:14px; font-size:15px;" name="%s"
             placeholder="%s"><br>""" % (i, i, i)

    html_start += """<button style="padding:4px; font-size:15px;" class="btn btn-primary">  %s </button>
          </form>
                              </div>
                        </div>""" % f_type

    return html_start


def create_table(columns, info):
    # Creates HTML <table> from the SQL output:

    html = """<div style="float:left"><table class="table table-bordered 
    table-striped table-hover"><thead><tr><th scope="col">#</th>"""

    for c in columns:
        html += """<th style="text-align:center;" scope="col">%s</th> """ % c

    html += """ </tr></thead><tbody class="table-group-divider">"""

    count = 1
    for row in info:
        html += """<tr><th scope="row">%i</th>""" % count
        for column in row:
            html += """<td style="text-align:center;">%s</td>""" % column
        count += 1
        html += """</tr>"""

    html += """</tbody></table></div>"""

    return html


def threaded(client, client_addr):
    while True:
        data = client.recv(1024).decode()
        if not data:
            client.close()
            break

        # This is the URL after localhost:XXXX
        # If we enter the browser "localhost:1234/addTable",
        # request variable will be "/addTable":
        request = data.split("\n")[0].split(" ")[1]

        # Establishing connection to SQL server with pyodbc library:
        connection = pyodbc.connect('Driver={SQL Server};Server=%s;Database=GTSTONE;Trusted_Connection=yes;' % server_name)

        # Cursor instance is what we use to execute queries:
        cursor = connection.cursor()

        if request == "/":  # If landing page:
            html = HTML_BEGIN + HTML_END
            content_length = "Content-Length: " + str(len(html))
            http_response = HTTP_VER + STATUS_OK + '\n' + content_length + "\n\n" + html
            client.sendall(http_response.encode())

        elif "table=" in request:
            title = """<h5 style="margin-bottom:20px; margin-top:20px;">%s</h5>""" % request.split("table=")[1].upper()
            table = request.split("table=")[1]
            cursor.execute('SELECT * FROM %s' % table)
            columns = []
            for i in cursor.description:
                columns.append(i[0])


            form_element = create_form(table.upper, table, columns, "Add")

            info = cursor.fetchall()
            html = create_table(columns, info)
            html = HTML_BEGIN + title + form_element + html + HTML_END
            content_length = "Content-Length: " + str(len(html))
            http_response = HTTP_VER + STATUS_OK + '\n' + content_length + "\n\n" + html
            client.sendall(http_response.encode())

        elif "view=" in request:
            title = """<h5 style="margin-bottom:20px; margin-top:20px;">%s</h5>""" % request.split("view=")[1].upper()
            table = request.split("view=")[1]

            # AnnualSales or tables about monthly incomes are shown ordered, others not:
            if table == "AnnualSales" or table == "MonthlyAvarageIncomes":
                cursor.execute('SELECT * FROM %s Order By Year desc' % table)
            elif "Month" in table:
                cursor.execute('SELECT * FROM %s Order By Year desc, Month desc' % table)
            else:
                cursor.execute('SELECT * FROM %s' % table)
            columns = []

            for i in cursor.description:
                columns.append(i[0])


            info = cursor.fetchall()
            html = create_table(columns, info)
            html = HTML_BEGIN + title + html + HTML_END
            content_length = "Content-Length: " + str(len(html))
            http_response = HTTP_VER + STATUS_OK + '\n' + content_length + "\n\n" + html
            client.sendall(http_response.encode())

        elif "Add" in request:
            table = request.split("?")[0].strip("/Add")
            columns = request.split("?")[1].split("&")


            # Creating a query like INSERT INTO (.....) VALUES (......)
            query = "INSERT INTO %s (" % (table)
            values = "VALUES ("
            for col in columns:
                query += col.split("=")[0] + ","
                if not col.isdigit():
                    values += "'" + col.split("=")[1] + "'" + ","
                else:
                    values += col.split("=")[1] + ","

            query = query[:-1] + ")"
            values = values[:-1] + ")"

            query = query + " " + values

            # Executing the query:
            cursor.execute(query)

            # We need to use .commit() whenever we use a query that makes changes to the database:
            connection.commit()

            # Refresh the page to show most recent state of the table:
            title = """<h5 style="margin-bottom:20px; margin-top:20px;">%s</h5>""" % table.upper()
            cursor.execute('SELECT * FROM %s' % table)
            columns = []
            for i in cursor.description:
                columns.append(i[0])


            form_element = create_form(table.upper, table, columns, "Add")

            info = cursor.fetchall()
            html = create_table(columns, info)
            html = HTML_BEGIN + title + form_element + html + HTML_END
            content_length = "Content-Length: " + str(len(html))
            http_response = HTTP_VER + STATUS_OK + '\n' + content_length + "\n\n" + html
            client.sendall(http_response.encode())

        else: # Invalid URL, responding with "Not Found":
            html = HTML_BEGIN + "NOT FOUND" + HTML_END
            content_length = "Content-Length: " + str(len(html))
            http_response = HTTP_VER + STATUS_OK + '\n' + content_length + "\n\n" + html
            client.sendall(http_response.encode())


def main():
    host = '0.0.0.0'
    port = 1234  # This

    server_socket= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    print("Socket binded to port", port)

    while True:
        server_socket.listen(5)
        print('Listening on port %s...' % port)
        client_socket, client_addr = server_socket.accept()
        start_new_thread(threaded, (client_socket, client_addr))


main()

