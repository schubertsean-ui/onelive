import { useEffect, useState } from "react";
import { Text, View, ScrollView } from "react-native";
import { fetchTonight } from "../services/api";

export default function Tonight() {
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    fetchTonight("Austin")
      .then(setItems)
      .catch((e) => setErr(String(e.message || e)));
  }, []);

  return (
    <ScrollView contentContainerStyle={{ padding: 20 }}>
      <Text style={{ fontSize: 22, fontWeight: "700" }}>Tonight</Text>
      {err ? <Text style={{ marginTop: 10, color: "red" }}>{err}</Text> : null}
      {items.map((e) => (
        <View key={e.event_id} style={{ padding: 12, borderWidth: 1, borderColor: "#ddd", borderRadius: 10, marginTop: 10 }}>
          <Text style={{ fontWeight: "700" }}>{e.venue?.name || "Venue"}</Text>
          <Text>{e.start_time || "-"}</Text>
          <Text>Confidence: {e.confidence}</Text>
        </View>
      ))}
    </ScrollView>
  );
}
