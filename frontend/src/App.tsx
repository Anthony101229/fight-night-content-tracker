import { Link, Route, Routes } from "react-router";
import { EventDetailPage } from "./pages/EventDetailPage";
import { EventsPage } from "./pages/EventsPage";

export function App() {
  return (
    <>
      <header className="app-header">
        <Link to="/" className="brand">
          Fight Night Content Tracker
        </Link>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<EventsPage />} />
          <Route path="/events/:id" element={<EventDetailPage />} />
          <Route path="*" element={<p>Page not found. <Link to="/">Back to events</Link></p>} />
        </Routes>
      </main>
    </>
  );
}
