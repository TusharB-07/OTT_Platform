from app import app, db
from models import User, Content, Movie, Series, Episode, Genre, Plan, Subscription, Payment, Watch, Review, ContentLanguage
from werkzeug.security import generate_password_hash
import datetime

def seed():
    with app.app_context():
        # Clear existing
        db.drop_all()
        db.create_all()

        # 1. Genres
        genres = [Genre(Genre_Name=name) for name in ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Thriller']]
        db.session.add_all(genres)
        db.session.commit()

        # 2. Plans
        plans = [
            Plan(Plan_Name='Basic', Price=199, Max_Screens=1, Duration_Days=30),
            Plan(Plan_Name='Standard', Price=499, Max_Screens=2, Duration_Days=30),
            Plan(Plan_Name='Premium', Price=799, Max_Screens=4, Duration_Days=30)
        ]
        db.session.add_all(plans)
        db.session.commit()

        # 3. Movies
        m1 = Movie(
            Title='Inception', Duration=148, Release_Year=2010, Content_Type='Movie',
            Movie_Name='Inception', Director='Christopher Nolan', Box_Office=836000000,
            Movie_Cast='Leonardo DiCaprio, Joseph Gordon-Levitt'
        )
        m2 = Movie(
            Title='The Dark Knight', Duration=152, Release_Year=2008, Content_Type='Movie',
            Movie_Name='The Dark Knight', Director='Christopher Nolan', Box_Office=1005000000,
            Movie_Cast='Christian Bale, Heath Ledger'
        )
        
        # 4. Series
        s1 = Series(Title='Stranger Things', Duration=50, Release_Year=2016, Content_Type='Series', Seasons=4)
        
        db.session.add_all([m1, m2, s1])
        db.session.commit()

        # 5. Episodes
        ep1 = Episode(ContentID=s1.ContentID, Episode_Title='Chapter One: The Vanishing of Will Byers', Season_No=1, Episode_No=1, Duration=48)
        ep2 = Episode(ContentID=s1.ContentID, Episode_Title='Chapter Two: The Weirdo on Maple Street', Season_No=1, Episode_No=2, Duration=45)
        db.session.add_all([ep1, ep2])

        # 6. M:N Relationships & Languages
        m1.genres.append(genres[0]) # Action
        db.session.commit()
        print("Database reverted to original sample data.")

if __name__ == "__main__":
    seed()
