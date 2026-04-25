export interface GeoPosition {
  latitude: number
  longitude: number
}

export function isGeolocationAvailable(): boolean {
  return typeof window !== 'undefined' && 'geolocation' in navigator
}

export function getCurrentPosition(): Promise<GeoPosition> {
  return new Promise((resolve, reject) => {
    if (!isGeolocationAvailable()) {
      reject(new Error('Geolocation nicht verfügbar'))
      return
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        })
      },
      (error) => {
        switch (error.code) {
          case error.PERMISSION_DENIED:
            reject(new Error('Standortzugriff verweigert'))
            break
          case error.POSITION_UNAVAILABLE:
            reject(new Error('Standort nicht verfügbar'))
            break
          case error.TIMEOUT:
            reject(new Error('Standortabfrage Timeout'))
            break
          default:
            reject(new Error('Standort konnte nicht ermittelt werden'))
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000,
      }
    )
  })
}
