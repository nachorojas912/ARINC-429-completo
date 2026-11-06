from app import create_app
from sqlalchemy.engine import make_url

app = create_app()


if __name__ == "__main__":
    database_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
    if database_url.drivername.startswith("sqlite"):
        database_target = database_url.database or "memoria"
        print(f"Base de datos activa: SQLite ({database_target})")
        print("Aviso: SQLite local no comparte datos con MySQL.")
    else:
        print(
            "Base de datos activa: "
            f"{database_url.drivername} en "
            f"{database_url.host}:{database_url.port}/{database_url.database}"
        )
    app.run(debug=True)
