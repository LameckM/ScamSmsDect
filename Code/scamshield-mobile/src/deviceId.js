import AsyncStorage from '@react-native-async-storage/async-storage'

const STORAGE_KEY = 'scamshield_device_id'

function generateId() {
  // Doesn't need to be cryptographically unguessable — it only needs to be
  // unique enough to distinguish reporters for trust-weighting on the
  // backend, not to be a security credential. Kept dependency-free rather
  // than pulling in expo-crypto just for this.
  const random = Math.random().toString(36).slice(2, 10)
  const timestamp = Date.now().toString(36)
  return `device-${timestamp}-${random}`
}

let cachedId = null

export async function getDeviceId() {
  if (cachedId) return cachedId

  let id = await AsyncStorage.getItem(STORAGE_KEY)
  if (!id) {
    id = generateId()
    await AsyncStorage.setItem(STORAGE_KEY, id)
  }

  cachedId = id
  return id
}
