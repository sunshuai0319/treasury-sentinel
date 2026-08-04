import "./styles.css";

export const metadata = {
  title: "Treasury Sentinel",
  description: "Policy-aware autonomous treasury guard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

