import AsyncStorage from '@react-native-async-storage/async-storage'

const HISTORY_KEY = 'scamshield_report_history'
const MAX_HISTORY_LENGTH = 50

export async function getHistory() {
  const raw = await AsyncStorage.getItem(HISTORY_KEY)
  return raw ? JSON.parse(raw) : []
}

export async function addToHistory(entry) {
  const history = await getHistory()
  const updated = [entry, ...history].slice(0, MAX_HISTORY_LENGTH)
  await AsyncStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  return updated
}
