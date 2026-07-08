import { Link } from "expo-router";
import { Text, View } from "react-native";

export default function Home() {
  return (
    <View style={{ padding: 20 }}>
      <Text style={{ fontSize: 22, fontWeight: "700" }}>One Live</Text>
      <Text style={{ marginTop: 8 }}>Truth-first "What's happening tonight?"</Text>
      <Link href="/tonight" style={{ marginTop: 18, fontSize: 16 }}>Open Tonight</Link>
    </View>
  );
}
