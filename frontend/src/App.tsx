import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Assistant from './pages/Assistant'
import Admissions from './pages/Admissions'
import Calculator from './pages/Calculator'
import Programs from './pages/Programs'
import Institutions from './pages/Institutions'
import Campuses from './pages/Campuses'
import Policies from './pages/Policies'
import Sources from './pages/Sources'
import About from './pages/About'
import Admin from './pages/Admin'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/admissions" element={<Admissions />} />
          <Route path="/calculator" element={<Calculator />} />
          <Route path="/programs" element={<Programs />} />
          <Route path="/institutions" element={<Institutions />} />
          <Route path="/campuses" element={<Campuses />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="/about" element={<About />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
