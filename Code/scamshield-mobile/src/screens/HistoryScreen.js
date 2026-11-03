import { useState, useEffect, useCallback } from 'react'
import { View, Text, FlatList, StyleSheet, RefreshControl } from 'react-native'
import { getHistory } from '../history'
import StatusPill from '../components/StatusPill'
import { colors, spacing, radius, typography } from '../theme'

export default function HistoryScreen() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(async () => {
    const data = await getHistory()
    setHistory(data)
    setLoading(false)
    setRefreshing(false)
  }, [])

  // App.js unmounts/remounts this screen on every tab switch (no navigation
  // library in use), so a plain mount-time load is enough to keep this
  // fresh each time the person opens the History tab.
  useEffect(() => {
    load()
  }, [load])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  if (loading) {
    return (
      <View style={styles.emptyState}>
        <Text style={styles.emptyText}>Loading…</Text>
      </View>
    )
  }

  if (history.length === 0) {
    return (
      <View style={styles.emptyState}>
        <Text style={styles.emptyText}>Reports you submit from this device will show up here.</Text>
      </View>
    )
  }

  return (
    <FlatList
      data={history}
      keyExtractor={(item, index) => `${item.submittedAt}-${index}`}
      contentContainerStyle={styles.listContent}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      renderItem={({ item }) => (
        <View style={styles.card}>
          <View style={styles.rowBetween}>
            <Text style={styles.number}>{item.number}</Text>
            <StatusPill status={item.status} />
          </View>
          <Text style={styles.message} numberOfLines={2}>
            {item.message}
          </Text>
          <View style={styles.rowBetween}>
            <Text style={styles.meta}>Score: {item.score}/100</Text>
            <Text style={styles.meta}>{new Date(item.submittedAt).toLocaleString()}</Text>
          </View>
        </View>
      )}
    />
  )
}

const styles = StyleSheet.create({
  emptyState: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  emptyText: { ...typography.body, color: colors.textSecondary, textAlign: 'center' },
  listContent: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  number: { ...typography.subtitle, color: colors.textPrimary, fontWeight: '700' },
  message: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.xs },
  meta: { fontSize: 11, color: colors.textMuted },
})
