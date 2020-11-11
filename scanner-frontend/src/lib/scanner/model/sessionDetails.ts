/**
 * RoboScan API
 * RoboScan API
 *
 * The version of the OpenAPI document: 1.0
 * 
 *
 * NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).
 * https://openapi-generator.tech
 * Do not edit the class manually.
 */


export interface SessionDetails { 
    /**
     * Session ID
     */
    id: number;
    /**
     * True if a scan is on-going
     */
    is_scanning: boolean;
    /**
     * True if the scanner supports skipping holes
     */
    feature_skip_hole: boolean;
}
