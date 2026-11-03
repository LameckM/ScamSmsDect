import { useState } from 'react'
import { SafeAreaView, View, Text, Pressable, StyleSheet } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import ReportScreen from './src/screens/ReportScreen'
import HistoryScreen from './src/screens/HistoryScreen'
import { colors, spacing, radius, typography } from './src/theme'

export default function App() {
  const [tab, setTab] = useState('report')

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="dark" />

      <View style={styles.header}>
        <Text style={styles.eyebrow}>ScamShield</Text>
        <Text style={styles.title}>Report a scam</Text>
      </View>

      <View style={styles.tabBar}>
        <Pressable
          style={[styles.tabButton, tab === 'report' && styles.tabButtonActive]}
          onPress={() => setTab('report')}
        >
          <Text style={[styles.tabLabel, tab === 'report' && styles.tabLabelActive]}>Report</Text>
        </Pressable>
        <Pressable
          style={[styles.tabButton, tab === 'history' && styles.tabButtonActive]}
          onPress={() => setTab('history')}
        >
          <Text style={[styles.tabLabel, tab === 'history' && styles.tabLabelActive]}>My reports</Text>
        </Pressable>
      </View>

      {tab === 'report' ? <ReportScreen /> : <HistoryScreen />}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  header: { paddingHorizontal: spacing.lg, paddingTop: spacing.md, paddingBottom: spacing.sm },
  eyebrow: { ...typography.label, color: colors.textMuted, marginBottom: 2 },
  title: { ...typography.title, color: colors.textPrimary },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: 4,
  },
  tabButton: { flex: 1, paddingVertical: 8, borderRadius: radius.sm, alignItems: 'center' },
  tabButtonActive: { backgroundColor: colors.primaryMuted },
  tabLabel: { ...typography.subtitle, color: colors.textSecondary },
  tabLabelActive: { color: colors.primary },
})
