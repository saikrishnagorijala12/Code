from hubsync import create_app

app = create_app()

def run():
    app.run(port=5000,host='localhost',debug=True)

if __name__ == '__main__':
    run()