import { Card, PageHeader, SourceLink } from '../components/ui'

export default function About() {
  return (
    <div>
      <PageHeader
        title="About"
        subtitle="Independent research project for Khyber Medical University admissions guidance."
      />
      <Card>
        <div className="space-y-4 text-slate-700">
          <p>
            <strong>MAHSUDo-guide</strong> is an independent source-aware university guidance API
            and web app for KMU admissions. It combines retrieval-grounded AI, a deterministic
            merit aggregate calculator, and rule-based eligibility checks.
          </p>
          <p>
            Every figure, rule, and claim cites its official source (KMU, PNMC, HEC). The backend
            enforces verification requirements: the calculator refuses to use unverified formulas.
          </p>
          <p>
            This is not an official KMU service. Always confirm current requirements on the
            official page before applying.
          </p>
          <div>
            <h3 className="font-semibold text-slate-900">Key sources</h3>
            <ul className="mt-2 space-y-1">
              <li>
                KMU CAS Admissions Policy (2025-26):{' '}
                <SourceLink url="https://cas.kmu.edu.pk/sitedocuments/Admission-Policy-Public-2025-26.pdf" title="PDF" />
              </li>
              <li>
                KMU BS Admissions Portal: <SourceLink url="https://bsadmissions.kmu.edu.pk/" title="bsadmissions.kmu.edu.pk" />
              </li>
              <li>
                KMU Main Site: <SourceLink url="https://kmu.edu.pk/" title="kmu.edu.pk" />
              </li>
              <li>
                PNMC: <SourceLink url="https://online.pnmc.gov.pk/" title="pnmc.gov.pk" />
              </li>
              <li>
                HEC: <SourceLink url="https://www.hec.gov.pk/" title="hec.gov.pk" />
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  )
}