// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the License);
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { useTranslation } from "react-i18next"

interface NotFoundProps {}

const NotFound: React.FunctionComponent<NotFoundProps> = ({}) => {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-center pt-24 md:pt-48 lg:pt-72">
      <div className="border-r px-6 text-3xl font-bold">404</div>
      <div className="px-6 text-lg">{t("not-found")}</div>
    </div>
  )
}

export default NotFound
