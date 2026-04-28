import csv
from app import app, db
from models import Content, Movie, Series, Genre, ContentLanguage

def import_data(file_path):
    with app.app_context():
        # Clear existing content related data (optional, but good for clean seed)
        # Note: Be careful with relationships
        print("Starting data import...")
        
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # 1. Pre-fetch or create Genres
            genre_map = {}
            all_genres = Genre.query.all()
            for g in all_genres:
                genre_map[g.Genre_Name] = g
            
            count = 0
            for row in reader:
                try:
                    title = row['Title']
                    year = int(row['Year'])
                    director = row['Director/Creator']
                    cast = row['Cast']
                    box_office = int(row['BoxOffice(USD)']) if row['BoxOffice(USD)'] else 0
                    duration = int(row['Duration(min)'])
                    genres_str = row['Genres']
                    content_type = row['Type']

                    # Check if already exists to avoid duplicates
                    if Content.query.filter_by(Title=title, Release_Year=year).first():
                        continue

                    # Create Content
                    if content_type == 'Movie':
                        item = Movie(
                            Title=title,
                            Duration=duration,
                            Release_Year=year,
                            Content_Type='Movie',
                            Movie_Name=title,
                            Director=director,
                            Box_Office=box_office,
                            Movie_Cast=cast
                        )
                    elif content_type == 'Series':
                        # For series, we assume seasons=1 for now as per CSV
                        item = Series(
                            Title=title,
                            Duration=duration,
                            Release_Year=year,
                            Content_Type='Series',
                            Seasons=1
                        )
                    else:
                        continue

                    # Add Genres
                    genre_names = [g.strip() for g in genres_str.split('|')]
                    for gname in genre_names:
                        if gname not in genre_map:
                            new_genre = Genre(Genre_Name=gname)
                            db.session.add(new_genre)
                            db.session.commit()
                            genre_map[gname] = new_genre
                        item.genres.append(genre_map[gname])

                    # Add default language
                    lang = ContentLanguage(Language='English')
                    item.languages.append(lang)

                    db.session.add(item)
                    count += 1
                    
                    if count % 20 == 0:
                        db.session.commit()
                        print(f"Imported {count} items...")

                except Exception as e:
                    print(f"Error importing row {row['Title']}: {e}")
                    db.session.rollback()

            db.session.commit()
            print(f"Successfully imported {count} items.")

if __name__ == "__main__":
    import_data('data.txt')
