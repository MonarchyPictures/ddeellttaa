from geopy.geocoders import Nominatim
from geopy.distance import geodesic

class GeoService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="intent_radar")
        # Cache for common locations to avoid timeouts
        self.cache = {
            "kenya": (1.2921, 36.8219),
            "nairobi": (1.2921, 36.8219),
            "mombasa": (-4.0435, 39.6682),
            "kisumu": (-0.0917, 34.7680),
            "nakuru": (-0.3031, 36.0800),
            "eldoret": (0.5143, 35.2698),
            "thika": (-1.0333, 37.0667),
            "machakos": (-1.5167, 37.2667),
            "kiambu": (-1.1667, 36.8333)
        }

    def get_coordinates(self, location_name):
        """Convert location name to lat/long."""
        if not location_name or location_name.lower() in ["unknown", "none", "null"]:
            return None, None
            
        loc_lower = location_name.lower().strip()
        
        # Check cache first
        if loc_lower in self.cache:
            return self.cache[loc_lower]
        
        # Partial match for common cities
        for city, coords in self.cache.items():
            if city in loc_lower:
                return coords
                
        try:
            # Add timeout to avoid hanging
            location = self.geolocator.geocode(location_name, timeout=3)
            if location:
                # Save to cache
                self.cache[loc_lower] = (location.latitude, location.longitude)
                return location.latitude, location.longitude
        except:
            pass
        
        # Default to Kenya coordinates if it mentions Kenya but specific town failed
        if "kenya" in loc_lower:
            return self.cache["kenya"]
            
        return None, None

    def calculate_distance(self, coords1, coords2):
        """Calculate distance in km between two points."""
        if not coords1 or not coords2:
            return None
        return geodesic(coords1, coords2).km

    def is_within_radius(self, center_coords, target_coords, radius_km):
        """Check if target is within radius of center."""
        if not center_coords or not target_coords:
            return True # If unknown, keep it
        distance = geodesic(center_coords, target_coords).km
        return distance <= radius_km
