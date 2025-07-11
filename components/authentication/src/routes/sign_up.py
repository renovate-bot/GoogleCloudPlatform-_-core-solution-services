# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Sign Up endpoints """
import requests
from copy import deepcopy
from fastapi import APIRouter
from requests.exceptions import ConnectTimeout
from config import ERROR_RESPONSES, FIREBASE_API_KEY, IDP_URL
from common.models import User
from common.utils.errors import (InvalidRequestPayloadError,
                                 UnauthorizedUserError)
from common.utils.http_exceptions import (BadRequest, InternalServerError,
                                          Unauthorized, ConnectionTimeout,
                                          ServiceUnavailable)
from common.utils.logging_handler import Logger
from schemas.sign_up_schema import (SignUpWithCredentialsModel,
                                    SignUpWithCredentialsResponseModel)
from schemas.error_schema import ConnectionErrorResponseModel
from services.create_session_service import create_session
from metrics import track_signup

Logger = Logger.get_logger(__file__)
ERROR_RESPONSE_DICT = deepcopy(ERROR_RESPONSES)
del ERROR_RESPONSE_DICT[401]
ERROR_RESPONSE_DICT[503] = {"model": ConnectionErrorResponseModel}

# pylint: disable = broad-exception-raised
router = APIRouter(
    tags=["Sign Up"],
    prefix="/sign-up",
    responses=ERROR_RESPONSE_DICT)


@router.post(
    "/credentials",
    response_model=SignUpWithCredentialsResponseModel)
@track_signup
def sign_up_with_credentials(credentials: SignUpWithCredentialsModel):
  """ This endpoint creates a new user with the given email and password
  by making an HTTP POST request to the IDP auth signUp endpoint and
  returns id token and refresh token.
  ### Args:
  credentials: `SignUpWithCredentialsModel`
    Credentials will consist of email and password
  ### Raises:
  UnauthorizedUserError:
    If the user does not exist in firestore <br/>
  ConnectionTimeout:
    Connection Timeout Error. If API request gets timed-out. <br/>
  Exception 500:
    Internal Server Error. Raised if something went wrong <br/>
  ServiceUnavailable:
    Connection Error. If other service being called internally is not available
  ### Returns:
  Token: `SignUpWithCredentialsResponseModel`
    Returns the id token as well as refresh token
  """
  try:
    user_data = User.find_by_email(credentials.email)
    if not user_data:
      raise UnauthorizedUserError("Unauthorized: User not found in database")
    if user_data.get_fields(reformat_datetime=True).get("status") == "inactive":
      raise UnauthorizedUserError("Unauthorized: User status is inactive")
    url = f"{IDP_URL}:signUp?key={FIREBASE_API_KEY}"
    data = {
        "email": credentials.email,
        "password": credentials.password,
        "returnSecureToken": True
    }
    resp = requests.post(url, data, timeout=60)
    resp_data = resp.json()
    Logger.info("IDP SIGNUP RESPONSE", extra={"response_data": resp_data})
    if resp.status_code == 200:
      res = resp.json()
      res["user_id"] = user_data.user_id
      session_res = create_session(user_data.user_id)
      Logger.info("SESSION_RES: ", extra={"session_data": session_res})
      res["session_id"] = session_res.get("session_id")
      return {"success": True, "message": "Successfully signed up", "data": res}
    if resp.status_code == 400:
      res = resp.json()
      raise InvalidRequestPayloadError(res.get("error").get("message"))
    if resp.status_code == 403:
      raise Exception("Firebase API key missing")
  except UnauthorizedUserError as e:
    raise Unauthorized(str(e)) from e
  except InvalidRequestPayloadError as e:
    raise BadRequest(str(e)) from e
  except ConnectTimeout as e:
    raise ConnectionTimeout(str(e)) from e
  except ConnectionError as e:
    raise ServiceUnavailable(str(e)) from e
  except Exception as e:
    raise InternalServerError(str(e)) from e
