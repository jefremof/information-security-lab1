_page = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Records List</title>
</head>

<body>
    <h1>Records:</h1>
    <ul>
        {content}
    </ul>
    
</body>

</html>
"""

def render_page(records):
    content = "\n".join([f"<li>{record}</li>" for record in records])
    return _page.format(content=content)